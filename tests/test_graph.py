"""Tests for component graph service."""

import pytest
from pathlib import Path
from textwrap import dedent

from rendered.services.htmpl_admin.graph import (
    build_component_ttl,
    ComponentGraph,
    extract_config_key,
)


class TestExtractConfigKey:
    """Tests for parsing jinja conditional directory names."""

    def test_simple_conditional(self):
        assert extract_config_key("{% if auth %}auth{% endif %}") == "auth"

    def test_conditional_with_different_name(self):
        assert extract_config_key("{% if use_redis %}redis{% endif %}") == "use_redis"

    def test_conditional_with_spaces(self):
        assert extract_config_key("{%  if  oauth  %}oauth{%  endif  %}") == "oauth"

    def test_no_conditional(self):
        assert extract_config_key("htmpl_admin") is None

    def test_plain_name(self):
        assert extract_config_key("auth") is None


@pytest.fixture
def template_dir(tmp_path: Path) -> Path:
    """Create a sample template structure for testing."""
    # Mimic copier template structure: template/{{name}}/{{module}}/...
    module = tmp_path / "template" / "{{name}}" / "{{module}}"
    components = module / "components"
    services = module / "services"
    components.mkdir(parents=True)
    services.mkdir(parents=True)

    # Auth component with conditional directory name
    auth = components / "{% if auth %}auth{% endif %}"
    auth.mkdir()
    (auth / "component.toml").write_text(
        dedent(
            """
        [project]
        name = "auth"
        uri = "components/auth"
        description = "Authentication components"
        readme = "README.md"
        help = "Login and registration forms"
        dependencies = ["htmpl:services/oauth", "python:pyjwt>=2.8.0"]
    """
        ).strip()
    )
    (auth / "README.md").write_text(
        dedent(
            """
        # Auth Component

        Provides login and registration.

        ```python
        from auth import login
        ```
    """
        ).strip()
    )

    # Forms component (always included, no conditional)
    forms = components / "forms"
    forms.mkdir()
    (forms / "component.toml").write_text(
        dedent(
            """
        [project]
        name = "forms"
        uri = "components/forms"
        description = "Form components"
    """
        ).strip()
    )

    # OAuth service with conditional
    oauth = services / "{% if oauth %}oauth{% endif %}"
    oauth.mkdir()
    (oauth / "component.toml").write_text(
        dedent(
            """
        [project]
        name = "oauth"
        uri = "services/oauth"
        description = "OAuth2 service"
        help = "Provides OAuth2 authentication"
        dependencies = ["htmpl:services/redis", "python:authlib>=1.0"]
    """
        ).strip()
    )

    # Redis service (always included)
    redis = services / "redis"
    redis.mkdir()
    (redis / "component.toml").write_text(
        dedent(
            """
        [project]
        name = "redis"
        uri = "services/redis"
        description = "Redis service"
    """
        ).strip()
    )

    return tmp_path / "template"


@pytest.fixture
def ttl_file(template_dir: Path, tmp_path: Path) -> Path:
    """Generate TTL file from template."""
    ttl_content = build_component_ttl(template_dir)
    ttl_path = tmp_path / "project" / "components.ttl"
    ttl_path.parent.mkdir(parents=True, exist_ok=True)
    ttl_path.write_text(ttl_content)
    return ttl_path


@pytest.fixture
def project_dir(ttl_file: Path) -> Path:
    """Project directory containing components.ttl."""
    return ttl_file.parent


class TestBuildComponentTTL:
    """Tests for TTL generation from template directory."""

    def test_generates_valid_prefixes(self, template_dir: Path):
        ttl = build_component_ttl(template_dir)
        assert "@prefix htmpl: <htmpl://> ." in ttl
        assert "@prefix dep: <htmpl://depends/> ." in ttl

    def test_includes_component_name(self, template_dir: Path):
        ttl = build_component_ttl(template_dir)
        assert '<htmpl://components/auth> htmpl:name "auth"' in ttl

    def test_includes_config_key_for_conditionals(self, template_dir: Path):
        ttl = build_component_ttl(template_dir)
        assert '<htmpl://components/auth> htmpl:configKey "auth"' in ttl
        assert '<htmpl://services/oauth> htmpl:configKey "oauth"' in ttl

    def test_no_config_key_for_always_included(self, template_dir: Path):
        ttl = build_component_ttl(template_dir)
        # forms and redis don't have conditionals
        assert "<htmpl://components/forms> htmpl:configKey" not in ttl
        assert "<htmpl://services/redis> htmpl:configKey" not in ttl

    def test_includes_dependencies(self, template_dir: Path):
        ttl = build_component_ttl(template_dir)
        assert "<htmpl://components/auth> dep:requires <htmpl://services/oauth>" in ttl
        assert '<htmpl://components/auth> dep:python "pyjwt>=2.8.0"' in ttl

    def test_includes_help_text(self, template_dir: Path):
        ttl = build_component_ttl(template_dir)
        assert (
            '<htmpl://components/auth> htmpl:help "Login and registration forms"' in ttl
        )

    def test_includes_readme_base64(self, template_dir: Path):
        ttl = build_component_ttl(template_dir)
        # README should be base64 encoded
        assert '<htmpl://components/auth> htmpl:readme "' in ttl
        # Should not contain raw markdown
        assert "# Auth Component" not in ttl

    def test_handles_empty_template(self, tmp_path: Path):
        empty = tmp_path / "empty_template"
        empty.mkdir()
        ttl = build_component_ttl(empty)
        lines = [l for l in ttl.strip().split("\n") if l]
        assert len(lines) == 3  # Just the prefixes


class TestComponentGraph:
    """Tests for the ComponentGraph class."""

    def test_loads_ttl_file(self, project_dir: Path):
        graph = ComponentGraph(project_dir=project_dir)
        assert graph.graph is not None

    def test_get_deps_returns_transitive_dependencies(self, project_dir: Path):
        graph = ComponentGraph(project_dir=project_dir)
        deps = graph.get_deps("components/auth")
        assert "services/oauth" in deps
        assert "services/redis" in deps  # Transitive through oauth

    def test_get_deps_empty_for_leaf(self, project_dir: Path):
        graph = ComponentGraph(project_dir=project_dir)
        deps = graph.get_deps("services/redis")
        assert deps == set()

    def test_get_python_deps(self, project_dir: Path):
        graph = ComponentGraph(project_dir=project_dir)
        deps = graph.get_python_deps("components/auth")
        assert "pyjwt>=2.8.0" in deps
        # Transitive: auth -> oauth -> authlib
        assert "authlib>=1.0" in deps

    def test_detects_installed_components(self, project_dir: Path):
        (project_dir / "components" / "auth").mkdir(parents=True)

        graph = ComponentGraph(project_dir=project_dir)
        installed = graph.get_installed()
        assert "components/auth" in installed

    def test_resolve_excludes_installed(self, project_dir: Path):
        (project_dir / "services" / "redis").mkdir(parents=True)

        graph = ComponentGraph(project_dir=project_dir)
        needed = graph.resolve(["components/auth"])

        assert "services/redis" not in needed  # Already installed
        assert "services/oauth" in needed
        assert "components/auth" in needed

    def test_get_config_keys(self, project_dir: Path):
        graph = ComponentGraph(project_dir=project_dir)
        keys = graph.get_config_keys(
            ["components/auth", "services/oauth", "services/redis"]
        )

        assert keys == {
            "auth": "components/auth",
            "oauth": "services/oauth",
        }
        # redis has no config key (always included)
        assert "redis" not in keys

    def test_all_components_returns_metadata(self, project_dir: Path):
        (project_dir / "components" / "auth").mkdir(parents=True)

        graph = ComponentGraph(project_dir=project_dir)
        components = graph.all_components()

        auth = next(c for c in components if c["uri"] == "components/auth")
        assert auth["name"] == "auth"
        assert auth["config_key"] == "auth"
        assert auth["installed"] is True
        assert auth["help"] == "Login and registration forms"

        redis = next(c for c in components if c["uri"] == "services/redis")
        assert redis["config_key"] is None  # Always included

    def test_get_component(self, project_dir: Path):
        graph = ComponentGraph(project_dir=project_dir)
        component = graph.get_component("components/auth")

        assert component is not None
        assert component["name"] == "auth"
        assert component["uri"] == "components/auth"
        assert component["config_key"] == "auth"

    def test_get_component_not_found(self, project_dir: Path):
        graph = ComponentGraph(project_dir=project_dir)
        component = graph.get_component("components/nonexistent")
        assert component is None

    def test_get_readme(self, project_dir: Path):
        graph = ComponentGraph(project_dir=project_dir)
        readme = graph.get_readme("components/auth")

        assert readme is not None
        assert "# Auth Component" in readme
        assert "```python" in readme

    def test_get_readme_not_found(self, project_dir: Path):
        graph = ComponentGraph(project_dir=project_dir)
        readme = graph.get_readme("components/forms")
        assert readme is None


class TestRealTemplate:
    """Integration tests against the actual template directory."""

    @pytest.fixture
    def real_template(self) -> Path:
        """Path to the actual template directory."""
        template = Path(__file__).parent.parent / "template"
        if not template.exists():
            pytest.skip("template/ directory not found")
        return template

    def test_can_build_ttl_from_template(self, real_template: Path):
        """Verify TTL generation works with real template."""
        ttl = build_component_ttl(real_template)
        assert "@prefix htmpl:" in ttl

    def test_auth_component_has_config_key(self, real_template: Path, tmp_path: Path):
        """Verify auth component is correctly parsed."""
        ttl = build_component_ttl(real_template)
        ttl_path = tmp_path / "components.ttl"
        ttl_path.write_text(ttl)

        graph = ComponentGraph(components_ttl=ttl_path)
        components = graph.all_components()

        # Find auth if it exists
        auth_components = [c for c in components if "auth" in c["uri"]]
        if auth_components:
            auth = auth_components[0]
            assert auth["config_key"] is not None
