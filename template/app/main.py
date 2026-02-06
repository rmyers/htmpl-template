import asyncio
from pathlib import Path
from cuneus import build_app
from cuneus.ext.otel import OTelExtension, OTelSettings
from htmpl.fastapi import add_assets_routes
from svcs.fastapi import DepContainer

from .services.htmpl_admin.service import HTMPLAdmin
from .services.observe import ObservabilityExtension, StoreSpanExporter, InMemoryStore
from .settings import AppSettings

store = InMemoryStore()
otel_settings = OTelSettings(instrument_fastapi=True)

app, cli, lifespan = build_app(
    HTMPLAdmin,
    OTelExtension(settings=otel_settings, span_exporters=[StoreSpanExporter(store)]),
    ObservabilityExtension(store=store),
    settings=AppSettings(),
)

add_assets_routes(app)


@app.get("/test-trace")
async def test_trace(container: DepContainer):
    from opentelemetry.trace import Tracer

    await asyncio.sleep(0.1)
    tracer = await container.aget(Tracer)
    with tracer.start_as_current_span("test-span") as span:
        await asyncio.sleep(0.1)
        span.add_event(name="blank", attributes={"test": "one"})
        await asyncio.sleep(0.5)
        span.add_event(name="slower", attributes={"test": "test"})
        with tracer.start_span("second") as span2:
            await asyncio.sleep(0.1)
            span.add_event(name="blank", attributes={"test": "one"})

    return {"ok": True}


@app.get("/debug-middleware")
async def debug_middleware():
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    return {
        "middleware": [str(m) for m in app.user_middleware],
        "instrumented": FastAPIInstrumentor().is_instrumented_by_opentelemetry,
    }


__all__ = ["app", "cli", "lifespan"]
