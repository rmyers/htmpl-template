from __future__ import annotations

from typing import Any

import structlog
import svcs
from fastapi import FastAPI

from cuneus import BaseExtension, Settings
from .store import Store, InMemoryStore
from .routes import router

logger = structlog.stdlib.get_logger(__name__)


class ObservabilitySettings(Settings):
    """Observability admin configuration."""

    enabled: bool = True
    prefix: str = "/admin"


class ObservabilityExtension(BaseExtension):
    """
    Observability admin panel extension.

    Provides a web UI for viewing traces and exceptions.

    Usage:
        from cuneus.ext.observability import ObservabilityExtension, InMemoryStore, StoreSpanExporter
        from cuneus.ext.otel import OTelExtension

        store = InMemoryStore()

        app, cli, lifespan = build_app(
            OTelExtension(span_exporters=[StoreSpanExporter(store)]),
            ObservabilityExtension(store=store),
        )
    """

    def __init__(
        self,
        settings: ObservabilitySettings | None = None,
        store: Store | None = None,
    ):
        self.settings = settings or ObservabilitySettings()
        self.store = store or InMemoryStore()

    async def startup(self, registry: svcs.Registry, app: FastAPI) -> dict[str, Any]:
        registry.register_value(Store, self.store)

        logger.info(
            "Observability admin started",
            prefix=self.settings.prefix,
        )

        return {"observability_store": self.store}

    def add_routes(self, app: FastAPI) -> None:
        app.include_router(router, prefix=self.settings.prefix)
