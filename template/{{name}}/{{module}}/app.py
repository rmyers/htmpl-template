from pathlib import Path
from fastapi import FastAPI
from cuneus import ExceptionExtension, build_lifespan
from cuneus.middleware import logging
from cuneus.ext import health
from htmpl.fastapi import add_assets_routes

from .services.htmpl_admin.service import HTMPLAdmin
from .settings import settings


def create_app() -> FastAPI:
    lifespan = build_lifespan(
        settings,
        ExceptionExtension(settings),
        logging.LoggingExtension(settings),
        health.HealthExtension(settings),
        HTMPLAdmin(project_dir=Path(".")),
    )
    app = FastAPI(lifespan=lifespan)
    app.add_middleware(logging.LoggingMiddleware)

    add_assets_routes(app)

    return app


app = create_app()
