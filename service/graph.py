"""Component graph service."""

import tomllib
import re
from pathlib import Path
from rdflib import Graph, Namespace, Literal

HTMPL = Namespace("htmpl://")
DEP = Namespace("htmpl://depends/")
STATUS = Namespace("htmpl://status/")


def build_component_ttl(components_dir: Path) -> str:
    lines = [
        "@prefix htmpl: <htmpl://> .",
        "@prefix dep: <htmpl://depends/> .",
    ]

    for toml_path in components_dir.rglob("component.toml"):
        config = tomllib.loads(toml_path.read_text())["project"]
        uri = config["name"]

        for d in config.get("dependencies", []):
            lines.append(f"htmpl:{uri} dep:requires {d} .")

        if config.get("help"):
            lines.append(f'htmpl:{uri} htmpl:help "{config["help"]}" .')

    return "\n".join(lines)


class ComponentGraph:
    def __init__(self, components_ttl: Path, project_dir: Path):
        self.graph = Graph()
        self.graph.bind("htmpl", HTMPL)
        self.graph.bind("dep", DEP)
        self.graph.bind("status", STATUS)
        self.project_dir = project_dir

        self.graph.parse(components_ttl, format="turtle")
        self._scan_installed()

    def _scan_installed(self):
        """Check filesystem for installed components."""
        for uri in self._all_uris():
            path = self.project_dir / "components" / uri
            if path.exists():
                self.graph.add((HTMPL[uri], STATUS.installed, Literal(True)))

    def _all_uris(self) -> set[str]:
        results = self.graph.query(
            """
            SELECT DISTINCT ?uri WHERE {
                { ?uri dep:requires ?_ } UNION { ?_ dep:requires ?uri }
            }
        """
        )
        return {str(row.uri).replace(str(HTMPL), "") for row in results}

    def get_deps(self, uri: str) -> set[str]:
        results = self.graph.query(
            f"""
            SELECT ?dep WHERE {{
                htmpl:{uri} dep:requires+ ?dep .
            }}
        """
        )
        return {str(row.dep).replace(str(HTMPL), "") for row in results}

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

    def all_components(self) -> list[dict]:
        installed = self.get_installed()
        results = self.graph.query(
            """
            SELECT DISTINCT ?uri ?help WHERE {
                { ?uri dep:requires ?_ } UNION { ?_ dep:requires ?uri }
                OPTIONAL { ?uri htmpl:help ?help }
            }
        """
        )
        return [
            {
                "uri": (uri := str(row.uri).replace(str(HTMPL), "")),
                "help": str(row.help) if row.help else "",
                "installed": uri in installed,
            }
            for row in results
        ]


if __name__ == "__main__":
    components = Path("template") / "{{name}}" / "{{module}}" / "components"
    print(build_component_ttl(components_dir=components))
