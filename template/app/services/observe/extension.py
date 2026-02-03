# cuneus/ext/observability/extension.py
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import svcs
from fastapi import FastAPI

from cuneus import BaseExtension, Settings
from .store import Store, InMemoryStore
from .routes import create_router

logger = logging.getLogger(__name__)


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
        store: Store | None = None,
        settings: ObservabilitySettings | None = None,
    ):
        self.settings = settings or ObservabilitySettings()
        self.store = store or InMemoryStore()

    @asynccontextmanager
    async def register(
        self, registry: svcs.Registry, app: FastAPI
    ) -> AsyncIterator[dict[str, Any]]:
        registry.register_value(Store, self.store)

        logger.info(
            "Observability admin started",
            extra={"prefix": self.settings.prefix},
        )

        yield {"observability_store": self.store}

    def add_routes(self, app: FastAPI) -> None:
        if not self.settings.enabled:
            return

        router = create_router(self.store)
        app.include_router(router, prefix=self.settings.prefix)
