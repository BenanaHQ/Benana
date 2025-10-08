from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, APIRouter


@dataclass(frozen=True)
class Permission:
    key: str
    description: str | None = None


class BasePlugin(ABC):
    name: str
    version: str
    description: str = ""
    is_core: bool = False
    dependencies: list[str] = []

    @staticmethod
    @abstractmethod
    def migrations_path() -> Path:
        """Return the path to the plugin's migrations directory."""

    @abstractmethod
    def on_load(self, ctx: dict[str, Any]) -> None:
        """Called after migrations but before route registration."""

    @abstractmethod
    def register_routes(self, app: FastAPI, router: APIRouter) -> None:
        """Register FastAPI routes."""

    def register_permissions(self) -> list[Permission]:  # optional
        return []

    def seed(self, db) -> None:  # optional
        return None

    def on_unload(self, ctx: dict[str, Any]) -> None:  # optional
        return None

