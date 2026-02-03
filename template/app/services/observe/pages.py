from string.templatelib import Template

from .store import DashboardStats, TraceRecord, SpanRecord, ExceptionRecord


def _layout(children, title: str = "Observation") -> Template:
    return t"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} · Admin</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
    <script src="https://unpkg.com/htmx.org@2"></script>
    <style>
        :root {{ --pico-font-size: 15px; }}
        .admin-grid {{ display: grid; grid-template-columns: 180px 1fr; min-height: 100vh; }}
        .admin-nav {{ background: var(--pico-card-background-color); border-right: 1px solid var(--pico-muted-border-color); padding: 1rem; }}
        .admin-nav ul {{ padding: 0; margin-top: 1rem; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1rem; }}
        .stat-card {{ text-align: center; }}
        .stat-card strong {{ font-size: 1.75rem; display: block; }}
        .waterfall-track {{ height: 1.25rem; background: var(--pico-muted-border-color); border-radius: 3px; position: relative; }}
        .waterfall-bar {{ height: 100%; border-radius: 3px; position: absolute; }}
        .waterfall-bar.ok {{ background: var(--pico-primary); }}
        .waterfall-bar.error {{ background: var(--pico-del-color); }}
        pre {{ font-size: 0.8rem; }}
    </style>
</head>
<body>
    <div class="admin-grid">
        <aside class="admin-nav">
            <strong>Admin</strong>
            <nav>
                <ul>
                    <li><a href="/admin">Dashboard</a></li>
                    <li><a href="/admin/traces">Traces</a></li>
                    <li><a href="/admin/exceptions">Exceptions</a></li>
                </ul>
            </nav>
        </aside>
        <main class="container">
            <h1>{title}</h1>
            {children}
        </main>
    </div>
</body>
</html>"""


def _time_ago(dt) -> Template:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    delta = now - dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else now - dt

    seconds = int(delta.total_seconds())
    if seconds < 60:
        return t"just now"
    if seconds < 3600:
        return t"{seconds // 60}m ago"
    if seconds < 86400:
        return t"{seconds // 3600}h ago"
    return t"{seconds // 86400}d ago"


def _badge(status: str) -> Template:
    if status == "ERROR":
        return t'<mark data-status="error">ERROR</mark>'
    return t"<kbd>OK</kbd>"


def _pagination(page: int, total_pages: int, base_url: str) -> Template:
    if total_pages <= 1:
        return t""

    prev_link = (
        t'<a href="{base_url}?page={page - 1}">←</a>'
        if page > 1
        else t'<span aria-disabled="true">←</span>'
    )
    next_link = (
        t'<a href="{base_url}?page={page + 1}">→</a>'
        if page < total_pages
        else t'<span aria-disabled="true">→</span>'
    )

    return t"""
    <nav>
        <ul>
            <li>{prev_link}</li>
            <li><span>{page} / {total_pages}</span></li>
            <li>{next_link}</li>
        </ul>
    </nav>
    """


# -----------------------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------------------


def dashboard_page(stats: DashboardStats) -> Template:
    traces_rows = t""
    for t in stats.recent_traces:
        traces_rows += t"""<tr>
            <td><a href="/admin/traces/{t.trace_id}"><code>{t.trace_id[:12]}…</code></a></td>
            <td>{t.root_span_name}</td>
            <td>{t.duration_ms}ms</td>
            <td>{_badge(t.status)}</td>
        </tr>"""

    exceptions_rows = t""
    for e in stats.recent_exceptions:
        exceptions_rows += t"""<tr>
            <td><a href="/admin/exceptions/{e.id}">{e.exc_type}</a></td>
            <td><small>{e.message[:50]}{'…' if len(e.message) > 50 else ''}</small></td>
            <td><small>{_time_ago(e.ts)}</small></td>
        </tr>"""

    return t"""
    <{_layout} title="Dashboard">
    <div class="stats-grid">
        <article class="stat-card">
            <small>Traces</small>
            <strong>{stats.trace_count}</strong>
        </article>
        <article class="stat-card">
            <small>Errors</small>
            <strong>{stats.error_count}</strong>
        </article>
        <article class="stat-card">
            <small>Error Rate</small>
            <strong>{stats.error_rate:.1f}%</strong>
        </article>
        <article class="stat-card">
            <small>Avg Duration</small>
            <strong>{stats.avg_duration_ms:.0f}ms</strong>
        </article>
    </div>

    <div class="grid">
        <article>
            <header>
                Recent Traces
                <a href="/admin/traces" role="button" class="outline secondary">View all</a>
            </header>
            <figure>
                <table>
                    <thead><tr><th>Trace</th><th>Name</th><th>Duration</th><th>Status</th></tr></thead>
                    <tbody>{traces_rows if traces_rows else '<tr><td colspan="4"><em>No traces</em></td></tr>'}</tbody>
                </table>
            </figure>
        </article>

        <article>
            <header>
                Recent Exceptions
                <a href="/admin/exceptions" role="button" class="outline secondary">View all</a>
            </header>
            <figure>
                <table>
                    <thead><tr><th>Type</th><th>Message</th><th>When</th></tr></thead>
                    <tbody>{exceptions_rows if exceptions_rows else '<tr><td colspan="3"><em>No exceptions</em></td></tr>'}</tbody>
                </table>
            </figure>
        </article>
    </div>
    </{_layout}>
    """


# -----------------------------------------------------------------------------
# Traces
# -----------------------------------------------------------------------------


def traces_page(
    traces: list[TraceRecord], page: int, total_pages: int, status_filter: str | None
) -> Template:
    rows = t""
    for t in traces:
        rows += t"""<tr>
            <td><a href="/admin/traces/{t.trace_id}"><code>{t.trace_id[:12]}…</code></a></td>
            <td>{t.root_span_name}</td>
            <td>{t.service}</td>
            <td><small>{t.started_at:%Y-%m-%d %H:%M:%S}</small></td>
            <td>{t.duration_ms}ms</td>
            <td>{_badge(t.status)}</td>
        </tr>"""

    return t"""
    <{_layout} title="Traces">
    <form method="get" action="/admin/traces">
        <fieldset role="group">
            <select name="status" onchange="this.form.submit()">
                <option value="">All statuses</option>
                <option value="OK" {'selected' if status_filter == 'OK' else ''}>OK</option>
                <option value="ERROR" {'selected' if status_filter == 'ERROR' else ''}>Error</option>
            </select>
        </fieldset>
    </form>

    <figure>
        <table>
            <thead>
                <tr><th>Trace</th><th>Name</th><th>Service</th><th>Time</th><th>Duration</th><th>Status</th></tr>
            </thead>
            <tbody>
                {rows if rows else '<tr><td colspan="6"><em>No traces</em></td></tr>'}
            </tbody>
        </table>
    </figure>

    {_pagination(page, total_pages, '/admin/traces')}
    </{_layout}>
    """


def trace_detail_page(trace: TraceRecord, spans: list[SpanRecord]) -> Template:
    waterfall = (
        _waterfall(spans, trace.duration_ms) if spans else t"<p><em>No spans</em></p>"
    )

    return t"""
    <{_layout} title="Trace: {trace.root_span_name}">
    <article>
        <header>
            <hgroup>
                <h2>{trace.root_span_name}</h2>
                <p><code>{trace.trace_id}</code></p>
            </hgroup>
        </header>
        <dl>
            <dt>Service</dt><dd>{trace.service}</dd>
            <dt>Duration</dt><dd>{trace.duration_ms}ms</dd>
            <dt>Status</dt><dd>{_badge(trace.status)}</dd>
            <dt>Started</dt><dd>{trace.started_at:%Y-%m-%d %H:%M:%S}</dd>
        </dl>
    </article>

    <article>
        <header>Spans ({len(spans)})</header>
        {waterfall}
    </article>
    </{_layout}>
    """


def _waterfall(spans: list[SpanRecord], total_ms: int) -> Template:
    if not spans or total_ms == 0:
        return t"<p><em>No spans</em></p>"

    trace_start = min(s.started_at for s in spans)
    rows = t""

    for span in spans:
        offset_ms = (span.started_at - trace_start).total_seconds() * 1000
        left_pct = (offset_ms / total_ms * 100) if total_ms else 0
        width_pct = max((span.duration_ms / total_ms * 100), 1) if total_ms else 0
        bar_class = "error" if span.status == "ERROR" else "ok"
        indent = "··" if span.parent_span_id else ""

        rows += t"""<tr>
            <td><code>{indent}{span.name}</code></td>
            <td style="width: 50%;">
                <div class="waterfall-track">
                    <div class="waterfall-bar {bar_class}" style="left: {left_pct:.1f}%; width: {width_pct:.1f}%;"></div>
                </div>
            </td>
            <td><small>{span.duration_ms}ms</small></td>
        </tr>"""

    return t"""
    <figure>
        <table>
            <thead><tr><th>Span</th><th>Timeline</th><th>Duration</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </figure>
    """


# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------


def exceptions_page(
    exceptions: list[ExceptionRecord], page: int, total_pages: int
) -> Template:
    rows = t""
    for e in exceptions:
        rows += t"""<tr>
            <td><a href="/admin/exceptions/{e.id}">{e.exc_type}</a></td>
            <td><small>{e.message[:60]}{'…' if len(e.message) > 60 else ''}</small></td>
            <td>
                {'<a href="/admin/traces/' + e.trace_id + '"><code>' + e.trace_id[:8] + '…</code></a>' if e.trace_id else '<em>—</em>'}
            </td>
            <td><small>{_time_ago(e.ts)}</small></td>
        </tr>"""

    return t"""
    <{_layout} title="Exceptions">
    <figure>
        <table>
            <thead><tr><th>Type</th><th>Message</th><th>Trace</th><th>When</th></tr></thead>
            <tbody>
                {rows if rows else '<tr><td colspan="4"><em>No exceptions</em></td></tr>'}
            </tbody>
        </table>
    </figure>

    {_pagination(page, total_pages, '/admin/exceptions')}
    </{_layout}>
    """


def exception_detail_page(exc: ExceptionRecord) -> Template:
    trace_link = (
        f'<a href="/admin/traces/{exc.trace_id}">{exc.trace_id}</a>'
        if exc.trace_id
        else "<em>Not linked</em>"
    )

    return t"""
    <{_layout} title="Exception: {exc.exc_type}">
    <article>
        <header>
            <hgroup>
                <h2>{exc.exc_type}</h2>
                <p>{exc.message}</p>
            </hgroup>
        </header>
        <dl>
            <dt>Time</dt><dd>{exc.ts:%Y-%m-%d %H:%M:%S}</dd>
            <dt>Trace</dt><dd>{trace_link}</dd>
            <dt>Fingerprint</dt><dd><code>{exc.fingerprint}</code></dd>
        </dl>
    </article>

    <article>
        <header>Traceback</header>
        <pre><code>{exc.tb}</code></pre>
    </article>

    {_context_section(exc.ctx)}
    </{_layout}>
    """


def _context_section(ctx: dict | None) -> Template:
    if not ctx:
        return t""

    import json

    return t"""
    <article>
        <header>Request Context</header>
        <pre><code>{json.dumps(ctx, indent=2)}</code></pre>
    </article>
    """
