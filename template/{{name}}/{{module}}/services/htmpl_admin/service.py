from pathlib import Path
from typing import Any
from cuneus import BaseExtension
from fastapi import FastAPI
from svcs import Registry, Container

from ...types import TComponentGraph
from .graph import ComponentGraph
from .routes import router


class HTMPLAdmin(BaseExtension):

    def __init__(self, debug: bool = False, project_dir: Path = Path("..")):
        self.debug = debug
        self.project_dir = project_dir

    def _graph_factory(self, container: Container) -> ComponentGraph:
        return ComponentGraph(project_dir=self.project_dir)

    async def startup(self, registry: Registry, app: FastAPI) -> dict[str, Any]:
        registry.register_factory(TComponentGraph, self._graph_factory)
        app.include_router(router)
        return await super().startup(registry, app)

    async def shutdown(self, app: FastAPI) -> None:
        return await super().shutdown(app)
