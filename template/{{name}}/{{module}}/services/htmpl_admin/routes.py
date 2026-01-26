"""HTMPL Admin dashboard routes."""

from fastapi import APIRouter, Request
from svcs.fastapi import DepContainer

import mistune
from tdom import html
from htmpl.core import SafeHTML, render_html

from ...types import TComponentGraph

router = APIRouter(prefix="/admin", tags=["admin"])


def render_markdown(content: str) -> SafeHTML:
    """Render markdown to HTML, marked safe for template insertion."""
    return SafeHTML(str(mistune.html(content)))


# Layout

def AdminPage(children, *, title: str = "HTMPL Admin"):
    return html(t'''<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
</head>
<body>
    <nav class="container">
        <ul>
            <li><a href="/admin"><strong>HTMPL Admin</strong></a></li>
        </ul>
        <ul>
            <li><a href="/admin">Components</a></li>
            <li><a href="/admin/resolve">Resolve</a></li>
        </ul>
    </nav>
    <main class="container">{children}</main>
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
    <script>hljs.highlightAll();</script>
</body>
</html>''')


# Templates

def StatusBadge(installed: bool):
    if installed:
        return t'<mark>Installed</mark>'
    return t'<mark class="secondary">Available</mark>'


def ComponentCard(component: dict, deps: set[str], python_deps: set[str]):
    uri = component["uri"]
    name = component["name"]
    help_text = component["help"] or "No description"
    config_key = component["config_key"]
    installed = component["installed"]

    config_info = t'<small><code>copier: {config_key}</code></small>' if config_key else t''

    dep_list = t''
    if deps:
        dep_items = [t'<li><a href="/admin/component/{d}">{d}</a></li>' for d in sorted(deps)]
        dep_list = t'<details><summary>Dependencies ({len(deps)})</summary><ul>{dep_items}</ul></details>'

    python_list = t''
    if python_deps:
        py_items = [t'<li><code>{p}</code></li>' for p in sorted(python_deps)]
        python_list = t'<details><summary>Python packages ({len(python_deps)})</summary><ul>{py_items}</ul></details>'

    return t'''
    <article>
        <header>
            <hgroup>
                <h3><a href="/admin/component/{uri}">{name}</a></h3>
                {StatusBadge(installed)}
            </hgroup>
        </header>
        {render_markdown(component["readme"])}
        <p><code>{uri}</code></p>
        <footer>
        {config_info}
        {dep_list}
        {python_list}
        </footer>
    </article>'''


def ComponentTable(components: list[dict]):
    rows = []
    for c in components:
        uri = c["uri"]
        rows.append(t'''<tr>
            <td><a href="/admin/component/{uri}">{c["name"]}</a></td>
            <td><code>{uri}</code></td>
            <td>{c["config_key"] or "-"}</td>
            <td>{StatusBadge(c["installed"])}</td>
        </tr>''')

    return t'''<table>
        <thead>
            <tr>
                <th>Name</th>
                <th>URI</th>
                <th>Config Key</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>'''


def ResolveForm(components: list[dict]):
    """Form to select components and resolve dependencies."""
    available = [c for c in components if not c["installed"] and c["config_key"]]

    checkboxes = []
    for c in available:
        checkboxes.append(t'''<label>
            <input type="checkbox" name="selected" value={c["uri"]}>
            {c["name"]} <small class="secondary">({c["uri"]})</small>
        </label>''')

    return t'''<form hx-post="/admin/resolve" hx-target="#resolve-result" hx-swap="innerHTML">
        <fieldset>
            <legend>Select components to install</legend>
            {checkboxes}
        </fieldset>
        <button type="submit">Resolve Dependencies</button>
    </form>
    <div id="resolve-result"></div>'''


def ResolveResult(needed: set[str], config_keys: dict[str, str], python_deps: set[str]):
    if not needed:
        return t'<article><p>All selected components are already installed.</p></article>'

    uri_items = [t'<li><code>{uri}</code></li>' for uri in sorted(needed)]

    copier_answers = " ".join(f"{k}=true" for k in sorted(config_keys.keys()))
    uv_command = f"uv add {' '.join(sorted(python_deps))}" if python_deps else None

    return t'''<article>
        <header><h4>Resolution Result</h4></header>

        <h5>Components to install ({len(needed)})</h5>
        <ul>{uri_items}</ul>

        <h5>Copier command</h5>
        <pre><code>copier update --data {copier_answers}</code></pre>

        {t'<h5>Python dependencies</h5><pre><code>{uv_command}</code></pre>' if uv_command else t''}
    </article>'''


# Routes

@router.get("")
async def admin_index(services: DepContainer):
    graph: TComponentGraph = await services.aget(TComponentGraph)
    components = graph.all_components()

    # Split into components and services
    comp_list = [c for c in components if c["uri"].startswith("components/")]
    svc_list = [c for c in components if c["uri"].startswith("services/")]

    installed_count = sum(1 for c in components if c["installed"])

    return await render_html(t'''
        <{AdminPage} title="HTMPL Admin - Dashboard">
        <hgroup>
            <h1>Component Dashboard</h1>
            <p>{len(components)} total components, {installed_count} installed</p>
        </hgroup>

        <section>
            <h2>Components ({len(comp_list)})</h2>
            {ComponentTable(comp_list)}
        </section>

        <section>
            <h2>Services ({len(svc_list)})</h2>
            {ComponentTable(svc_list)}
        </section>
        </{AdminPage}>
    ''')


@router.get("/component/{uri:path}")
async def component_detail(uri: str, services: DepContainer):
    graph: TComponentGraph = await services.aget(TComponentGraph)
    component = graph.get_component(uri)

    if not component:
        return await render_html(t'''
            <{AdminPage} title="Not Found">
            <h1>Component not found</h1>
            <p>No component with URI: <code>{uri}</code></p>
            <a href="/admin">Back to dashboard</a>
            </{AdminPage}>
        ''')

    deps = graph.get_deps(uri)
    python_deps = graph.get_python_deps(uri)

    return await render_html(t'''
        <{AdminPage} title="HTMPL Admin - {component["name"]}">
        <nav aria-label="breadcrumb">
            <ul>
                <li><a href="/admin">Dashboard</a></li>
                <li>{component["name"]}</li>
            </ul>
        </nav>

        {ComponentCard(component, deps, python_deps)}

        <a href="/admin" role="button" class="secondary">Back to Dashboard</a>
        </{AdminPage}>
    ''')


@router.get("/resolve")
async def resolve_page(services: DepContainer):
    graph: TComponentGraph = await services.aget(TComponentGraph)
    components = graph.all_components()

    return await render_html(t'''
        <{AdminPage} title="HTMPL Admin - Resolve">
        <hgroup>
            <h1>Resolve Dependencies</h1>
            <p>Select components to install and see all required dependencies</p>
        </hgroup>

        {ResolveForm(components)}
        </{AdminPage}>
    ''')


@router.post("/resolve")
async def resolve_dependencies(request: Request, services: DepContainer):
    graph: TComponentGraph = await services.aget(TComponentGraph)

    form = await request.form()
    selected = form.getlist("selected")

    if not selected:
        return await render_html(t'<article class="secondary"><p>No components selected.</p></article>')

    needed = graph.resolve(
        list(selected), # type: ignore
    )
    config_keys = graph.get_config_keys(list(needed))

    # Collect all python deps
    python_deps: set[str] = set()
    for uri in needed:
        python_deps |= graph.get_python_deps(uri)

    return await render_html(ResolveResult(needed, config_keys, python_deps))
