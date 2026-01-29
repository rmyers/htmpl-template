from pathlib import Path
from cuneus import build_app
from htmpl.fastapi import add_assets_routes

from .services.htmpl_admin.service import HTMPLAdmin
from .settings import AppSettings


app, cli = build_app(HTMPLAdmin, settings=AppSettings())

add_assets_routes(app)

__all__ = ["app", "cli"]
