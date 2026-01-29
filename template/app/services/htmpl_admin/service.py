from typing import Any

import click
from cuneus import BaseExtension
from fastapi import FastAPI
from svcs import Registry, Container

from .graph import ComponentGraph
from .routes import router
from ...settings import AppSettings
from ...types import TComponentGraph


class HTMPLAdmin(BaseExtension):

    def __init__(self, settings: AppSettings | None = None):
        self.settings = settings or AppSettings()

    def _graph_factory(self, container: Container) -> ComponentGraph:
        return ComponentGraph(project_dir=self.settings.project_dir)

    async def startup(self, registry: Registry, app: FastAPI) -> dict[str, Any]:
        registry.register_factory(TComponentGraph, self._graph_factory)
        app.include_router(router)
        return await super().startup(registry, app)

    async def shutdown(self, app: FastAPI) -> None:
        return await super().shutdown(app)

    def register_cli(self, cli: click.Group) -> None:
        @cli.group()
        @click.pass_context
        def htmpl(ctx: click.Context) -> None:
            """Cuneus CLI - FastAPI application framework."""
            ctx.ensure_object(dict)

        @htmpl.command()
        @click.option("--host", default="0.0.0.0", help="Bind host")
        @click.option("--port", default=8000, type=int, help="Bind port")
        def test_foo(host: str, port: int) -> None:
            print(host)
            print(port)
