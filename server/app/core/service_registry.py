from __future__ import annotations

from typing import Any, Dict


class ServiceRegistry:
    def __init__(self) -> None:
        self._services: Dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        self._services[name] = service

    def get(self, name: str) -> Any:
        return self._services[name]

    def unregister(self, name: str) -> None:
        self._services.pop(name, None)

