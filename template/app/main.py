from pathlib import Path
from cuneus import build_app
from htmpl.fastapi import add_assets_routes

from .services.htmpl_admin.service import HTMPLAdmin
from .services.observe.extension import ObservabilityExtension
from .settings import AppSettings


app, cli, lifespan = build_app(
    HTMPLAdmin,
    ObservabilityExtension(),
    settings=AppSettings(),
)

add_assets_routes(app)

__all__ = ["app", "cli", "lifespan"]
