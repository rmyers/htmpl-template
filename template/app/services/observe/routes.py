# cuneus/ext/observability/routes.py
from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from .store import Store
from .pages import (
    dashboard_page,
    traces_page,
    trace_detail_page,
    exceptions_page,
    exception_detail_page,
)


def create_router(store: Store) -> APIRouter:
    router = APIRouter()

    @router.get("", response_class=HTMLResponse)
    @router.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        stats = store.get_dashboard_stats()
        return dashboard_page(stats)

    @router.get("/traces", response_class=HTMLResponse)
    async def traces(
        request: Request,
        page: int = Query(1, ge=1),
        status: str | None = Query(None),
    ):
        items, total = store.get_traces(page=page, status=status)
        total_pages = (total + 49) // 50
        return traces_page(items, page, total_pages, status)

    @router.get("/traces/{trace_id}", response_class=HTMLResponse)
    async def trace_detail(request: Request, trace_id: str):
        trace = store.get_trace(trace_id)
        if not trace:
            return HTMLResponse("<h1>Trace not found</h1>", status_code=404)
        spans = store.get_spans_for_trace(trace_id)
        return trace_detail_page(trace, spans)

    @router.get("/exceptions", response_class=HTMLResponse)
    async def exceptions(request: Request, page: int = Query(1, ge=1)):
        items, total = store.get_exceptions(page=page)
        total_pages = (total + 49) // 50
        return exceptions_page(items, page, total_pages)

    @router.get("/exceptions/{exc_id}", response_class=HTMLResponse)
    async def exception_detail(request: Request, exc_id: int):
        exc = store.get_exception(exc_id)
        if not exc:
            return HTMLResponse("<h1>Exception not found</h1>", status_code=404)
        return exception_detail_page(exc)

    return router
