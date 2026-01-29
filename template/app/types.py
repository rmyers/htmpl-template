"""Protocol interfaces for htmpl services."""

from typing import Protocol


class TComponentGraph(Protocol):
    """Interface for component dependency graph.

    Provides dependency resolution and metadata for htmpl
    components and services.
    """

    def get_deps(self, uri: str) -> set[str]:
        """Get all transitive htmpl dependencies for a URI."""
        ...

    def get_python_deps(self, uri: str) -> set[str]:
        """Get Python package dependencies for a URI and its transitive deps."""
        ...

    def get_installed(self) -> set[str]:
        """Get URIs of all installed components."""
        ...

    def resolve(self, selected: list[str]) -> set[str]:
        """Return all URIs needed, excluding already installed."""
        ...

    def get_config_keys(self, uris: list[str]) -> dict[str, str]:
        """Get copier config keys for the given URIs.

        Returns dict mapping config_key -> uri.
        """
        ...

    def get_component(self, uri: str) -> dict | None:
        """Get metadata for a single component by URI.

        Returns dict with keys: uri, name, help, config_key, installed
        """
        ...

    def get_readme(self, uri: str) -> str | None:
        """Get decoded README content for a component."""
        ...

    def all_components(self) -> list[dict]:
        """Return metadata for all htmpl components."""
        ...
