from fastapi import FastAPI
from cuneus import ExceptionExtension, Settings, build_lifespan
from cuneus.middleware import logging
from cuneus.ext import health
from htmpl.fastapi import add_assets_routes

from .settings import settings


def create_app() -> FastAPI:
    lifespan = build_lifespan(
        settings,
        ExceptionExtension(settings),
        logging.LoggingExtension(settings),
        health.HealthExtension(settings),
    )
    app = FastAPI(lifespan=lifespan)
    app.add_middleware(logging.LoggingMiddleware)

    add_assets_routes(app)

    if settings.debug:
        from ._admin.manager import app as admin_app

        app.include_router(admin_app)

    return app


app = create_app()
