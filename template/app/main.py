from pathlib import Path
from cuneus import build_app
from cuneus.ext.otel import OTelExtension
from htmpl.fastapi import add_assets_routes

from .services.htmpl_admin.service import HTMPLAdmin
from .services.observe import ObservabilityExtension, StoreSpanExporter, InMemoryStore
from .settings import AppSettings

store = InMemoryStore()

app, cli, lifespan = build_app(
    HTMPLAdmin,
    OTelExtension(span_exporters=[StoreSpanExporter(store)]),
    ObservabilityExtension(store=store),
    settings=AppSettings(),
)

add_assets_routes(app)

__all__ = ["app", "cli", "lifespan"]
