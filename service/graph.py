"""Component graph service."""

from pathlib import Path
import tomllib
from rdflib import Graph, Namespace, Literal

HTMPL = Namespace("htmpl://")
DEP = Namespace("htmpl://depends/")
INSTALLED = Namespace("htmpl://installed/")


class ComponentGraph:
    def __init__(self):
        self.graph = Graph()
        self.graph.bind("htmpl", HTMPL)
        self.graph.bind("dep", DEP)
        self.graph.bind("installed", INSTALLED)

    def load_from_toml(self, components_dir: Path):
        """Build graph from component.toml files."""
        for toml_path in components_dir.rglob("component.toml"):
            config = tomllib.loads(toml_path.read_text())["component"]
            uri = config["uri"]

            for dep in config.get("depends", []):
                self.graph.add((HTMPL[uri], DEP.requires, HTMPL[dep]))

            if config.get("help"):
                self.graph.add((HTMPL[uri], HTMPL.help, Literal(config["help"])))

    def load_ttl(self, path: Path):
        """Load pre-built TTL file."""
        self.graph.parse(path, format="turtle")

    def save_ttl(self, path: Path):
        """Save graph to TTL."""
        self.graph.serialize(path, format="turtle")

    def mark_installed(self, uris: list[str]):
        """Mark components as installed."""
        for uri in uris:
            self.graph.add((HTMPL[uri], INSTALLED.active, Literal(True)))

    def get_deps(self, uri: str) -> set[str]:
        """Get all transitive deps for a component."""
        results = self.graph.query(
            f"""
            SELECT ?dep WHERE {{
                htmpl:{uri} dep:requires+ ?dep .
            }}
        """
        )
        return {str(row.dep).replace(str(HTMPL), "") for row in results}

    def get_dependents(self, uri: str) -> set[str]:
        """Get everything that depends on this component."""
        results = self.graph.query(
            f"""
            SELECT ?component WHERE {{
                ?component dep:requires+ htmpl:{uri} .
            }}
        """
        )
        return {str(row.component).replace(str(HTMPL), "") for row in results}

    def get_installed(self) -> set[str]:
        """Get all installed components."""
        results = self.graph.query(
            """
            SELECT ?uri WHERE {
                ?uri installed:active true .
            }
        """
        )
        return {str(row.uri).replace(str(HTMPL), "") for row in results}

    def resolve(self, selected: list[str]) -> set[str]:
        """Given selections, return all URIs needed including deps."""
        result = set(selected)
        for uri in selected:
            result |= self.get_deps(uri)
        return result

    def all_components(self) -> list[dict]:
        """List all components with metadata."""
        results = self.graph.query(
            """
            SELECT DISTINCT ?uri ?help WHERE {
                { ?uri dep:requires ?_ } UNION { ?_ dep:requires ?uri }
                OPTIONAL { ?uri htmpl:help ?help }
            }
        """
        )
        installed = self.get_installed()
        return [
            {
                "uri": str(row.uri).replace(str(HTMPL), ""),
                "help": str(row.help) if row.help else "",
                "installed": str(row.uri).replace(str(HTMPL), "") in installed,
            }
            for row in results
        ]
