"""Component graph service."""

import base64
import re
import tomllib
from pathlib import Path
from rdflib import Graph, Namespace, Literal
from structlog.stdlib import get_logger

logger = get_logger("html_admin")

HTMPL = Namespace("htmpl://")
DEP = Namespace("htmpl://depends/")
STATUS = Namespace("htmpl://status/")

# Match jinja conditionals like {% if auth %}auth{% endif %}
JINJA_CONDITIONAL_RE = re.compile(r"\{%\s*if\s+(\w+)\s*%\}.*?\{%\s*endif\s*%\}")

CURRENT_DIR = Path(__file__).parent


def parse_dependency(dep: str) -> tuple[str, str]:
    """Parse a dependency string into (namespace, value).

    Examples:
        "htmpl:services/oauth" -> ("htmpl", "services/oauth")
        "python:pyjwt>=2.8.0" -> ("python", "pyjwt>=2.8.0")
        "services/oauth" -> ("htmpl", "services/oauth")  # default
    """
    if ":" in dep and not dep.startswith("/"):
        ns, value = dep.split(":", 1)
        return ns, value
    return "htmpl", dep


def extract_config_key(dirname: str) -> str | None:
    """Extract copier config key from a jinja conditional directory name.

    Examples:
        "{% if auth %}auth{% endif %}" -> "auth"
        "{% if use_redis %}redis{% endif %}" -> "use_redis"
        "htmpl_admin" -> None (no conditional, always included)
    """
    match = JINJA_CONDITIONAL_RE.search(dirname)
    return match.group(1) if match else None


def build_component_ttl(template_dir: Path) -> str:
    """Build TTL from component.toml files in the template directory.

    Expects structure like:
        template/{{name}}/{{module}}/components/{% if auth %}auth{% endif %}/
        template/{{name}}/{{module}}/services/htmpl_admin/
    """
    lines = [
        "@prefix htmpl: <htmpl://> .",
        "@prefix dep: <htmpl://depends/> .",
        "",
    ]

    # Find the module directory (handles {{name}}/{{module}} pattern)
    module_dirs = list(template_dir.glob("*/*/"))
    if not module_dirs:
        return "\n".join(lines)

    module_dir = module_dirs[0]

    def process_component_dir(base_dir: Path, component_type: str):
        """Process components or services directory."""
        if not base_dir.exists():
            return

        for component_dir in base_dir.iterdir():
            if not component_dir.is_dir():
                continue

            toml_path = component_dir / "component.toml"
            if not toml_path.exists():
                continue

            config = tomllib.loads(toml_path.read_text())["project"]
            uri = config["uri"]
            name = config["name"]

            # Extract config key from directory name
            config_key = extract_config_key(component_dir.name)

            # Use full URI syntax since URIs contain slashes
            subject = f"<htmpl://{uri}>"

            # Add name mapping
            lines.append(f'{subject} htmpl:name "{name}" .')

            # Add config key if this is a conditional component
            if config_key:
                lines.append(f'{subject} htmpl:configKey "{config_key}" .')

            # Add dependencies
            for d in config.get("dependencies", []):
                ns, value = parse_dependency(d)
                if ns == "python":
                    # Python deps are literals for external package managers
                    lines.append(f'{subject} dep:python "{value}" .')
                else:
                    # Internal htmpl deps are graph nodes
                    lines.append(f"{subject} dep:requires <{ns}://{value}> .")

            # Add help text
            if help_text := config.get("help"):
                escaped = help_text.replace('"', '\\"')
                lines.append(f'{subject} htmpl:help "{escaped}" .')

            if readme_path := config.get("readme"):
                readme_file = component_dir / readme_path
                if readme_file.exists():
                    content = readme_file.read_bytes()
                    encoded = base64.b64encode(content).decode("ascii")
                    lines.append(f'{subject} htmpl:readme "{encoded}" .')

            lines.append("")  # Blank line between components

    process_component_dir(module_dir / "components", "component")
    process_component_dir(module_dir / "services", "service")

    return "\n".join(lines)


class ComponentGraph:
    def __init__(
        self,
        components_ttl: Path = CURRENT_DIR / "components.ttl",
        project_dir: Path | None = None,
    ):
        self.graph = Graph()
        self.graph.bind("htmpl", HTMPL)
        self.graph.bind("dep", DEP)
        self.graph.bind("status", STATUS)
        self.project_dir = project_dir or Path(".")

        # Load TTL from explicit path or discover from project
        if not components_ttl.exists():
            logger.info("Unable to locate ttl file")
        if components_ttl:
            ttl_path = components_ttl
        else:
            ttl_path = self._find_ttl()

        if ttl_path and ttl_path.exists():
            self.graph.parse(ttl_path, format="turtle")
            self._scan_installed()

    def _scan_installed(self):
        """Check filesystem for installed components."""
        for uri in self._all_uris():
            path = self.project_dir / uri
            if path.exists():
                self.graph.add((HTMPL[uri], STATUS.installed, Literal(True)))

    def _all_uris(self) -> set[str]:
        """Get all htmpl:// URIs (excluding python:// etc)."""
        results = self.graph.query(
            """
            SELECT DISTINCT ?uri WHERE {
                { ?uri dep:requires ?_ } UNION { ?_ dep:requires ?uri }
                FILTER(STRSTARTS(STR(?uri), "htmpl://"))
            }
        """
        )
        return {str(row.uri).replace(str(HTMPL), "") for row in results}

    def get_deps(self, uri: str) -> set[str]:
        """Get all transitive htmpl dependencies for a URI."""
        results = self.graph.query(
            f"""
            SELECT ?dep WHERE {{
                <htmpl://{uri}> dep:requires+ ?dep .
                FILTER(STRSTARTS(STR(?dep), "htmpl://"))
            }}
        """
        )
        return {str(row.dep).replace(str(HTMPL), "") for row in results}

    def get_python_deps(self, uri: str) -> set[str]:
        """Get Python package dependencies for a URI and its transitive deps."""
        # Get direct python deps
        direct = self.graph.query(
            f"""
            SELECT ?dep WHERE {{
                <htmpl://{uri}> dep:python ?dep .
            }}
        """
        )
        result = {str(row.dep) for row in direct}

        # Get python deps from transitive htmpl deps
        transitive = self.graph.query(
            f"""
            SELECT ?dep WHERE {{
                <htmpl://{uri}> dep:requires+ ?intermediate .
                ?intermediate dep:python ?dep .
            }}
        """
        )
        result |= {str(row.dep) for row in transitive}

        return result

    def get_installed(self) -> set[str]:
        results = self.graph.query(
            """
            SELECT ?uri WHERE {
                ?uri status:installed true .
            }
        """
        )
        return {str(row.uri).replace(str(HTMPL), "") for row in results}

    def resolve(self, selected: list[str]) -> set[str]:
        """Return all URIs needed, excluding already installed."""
        needed = set(selected)
        for uri in selected:
            needed |= self.get_deps(uri)
        return needed - self.get_installed()

    def get_config_keys(self, uris: list[str]) -> dict[str, str]:
        """Get copier config keys for the given URIs.

        Returns dict mapping config_key -> uri for components that have config keys.
        """
        results = self.graph.query(
            """
            SELECT ?uri ?key WHERE {
                ?uri htmpl:configKey ?key .
            }
        """
        )
        uri_to_key = {
            str(row.uri).replace(str(HTMPL), ""): str(row.key) for row in results
        }
        return {uri_to_key[uri]: uri for uri in uris if uri in uri_to_key}

    def all_components(self) -> list[dict]:
        """Return metadata for all htmpl components."""
        installed = self.get_installed()
        results = self.graph.query(
            """
            SELECT DISTINCT ?uri ?name ?help ?configKey WHERE {
                { ?uri dep:requires ?_ } UNION { ?_ dep:requires ?uri }
                FILTER(STRSTARTS(STR(?uri), "htmpl://"))
                OPTIONAL { ?uri htmpl:name ?name }
                OPTIONAL { ?uri htmpl:help ?help }
                OPTIONAL { ?uri htmpl:configKey ?configKey }
            }
        """
        )
        return [
            {
                "uri": (uri := str(row.uri).replace(str(HTMPL), "")),
                "name": str(row.name) if row.name else uri.split("/")[-1],
                "help": str(row.help) if row.help else "",
                "config_key": str(row.configKey) if row.configKey else None,
                "installed": uri in installed,
            }
            for row in results
        ]

    def get_component(self, uri: str) -> dict | None:
        """Get metadata for a single component by URI."""
        results = self.graph.query(
            f"""
            SELECT ?name ?help ?configKey ?readme WHERE {{
                <htmpl://{uri}> htmpl:name ?name .
                OPTIONAL {{ <htmpl://{uri}> htmpl:help ?help }}
                OPTIONAL {{ <htmpl://{uri}> htmpl:configKey ?configKey }}
                OPTIONAL {{ <htmpl://{uri}> htmpl:readme ?readme }}
            }}
        """
        )
        rows = list(results)
        if not rows:
            return None
        row = rows[0]
        installed = self.get_installed()
        encoded = str(row.readme) if row.readme else None
        readme = base64.b64decode(encoded).decode("utf-8") if encoded else ""
        return {
            "uri": uri,
            "name": str(row.name),
            "help": str(row.help) if row.help else "",
            "config_key": str(row.configKey) if row.configKey else None,
            "installed": uri in installed,
            "readme": readme,
        }

    def get_readme(self, uri: str) -> str | None:
        """Get decoded README content for a component."""
        results = self.graph.query(
            f"""
            SELECT ?readme WHERE {{
                <htmpl://{uri}> htmpl:readme ?readme .
            }}
        """
        )
        rows = list(results)
        if not rows:
            return None
        encoded = str(rows[0].readme)
        return base64.b64decode(encoded).decode("utf-8")

    def component_factory(self, component_cls: type):
        """Create a factory function for svcs registry.

        Usage:
            registry.register_factory(Component, graph.component_factory(Component))
        """

        def factory(uri: str):
            data = self.get_component(uri)
            if data is None:
                raise ValueError(f"Unknown component: {uri}")
            return component_cls(**data)

        return factory


if __name__ == "__main__":
    template = Path("template")
    print(build_component_ttl(template))
