from pathlib import Path
from cuneus import build_app
from cuneus.ext.otel import OTelExtension, OTelSettings
from htmpl.fastapi import add_assets_routes

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

__all__ = ["app", "cli", "lifespan"]
