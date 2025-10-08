from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, APIRouter

from server.app.core.plugin_spi import BasePlugin, Permission
from .routes import get_router


class PowerTablePlugin(BasePlugin):
    name = "powertable"
    version = "0.1.0"
    description = "PowerTable plugin"
    is_core = False

    @staticmethod
    def migrations_path() -> Path:
        return Path(__file__).parent / "migrations"

    def on_load(self, ctx: dict[str, Any]) -> None:
        services = ctx.get("services")
        services.register("powertable.echo", lambda x: x)

    def register_routes(self, app: FastAPI, router: APIRouter) -> None:
        sub = get_router()
        for route in sub.routes:
            router.routes.append(route)

    def register_permissions(self):
        return [
            Permission(key="powertable:view", description="View powertable"),
            Permission(key="powertable:edit", description="Edit powertable"),
        ]

    def seed(self, db) -> None:
        return None

    def on_unload(self, ctx: dict[str, Any]) -> None:
        return None


def get_plugin() -> BasePlugin:
    return PowerTablePlugin()

