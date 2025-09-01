from __future__ import annotations

from typing import Dict, List, Tuple

from .plugin_spi import Permission


class PermissionRegistry:
    def __init__(self) -> None:
        # maps plugin name to list of permissions
        self._perms: Dict[str, List[Permission]] = {}

    def register(self, plugin_name: str, permissions: List[Permission]) -> None:
        self._perms[plugin_name] = permissions or []

    def get_for_plugin(self, plugin_name: str) -> List[Permission]:
        return self._perms.get(plugin_name, [])

    def all(self) -> List[Tuple[str, Permission]]:
        out: List[Tuple[str, Permission]] = []
        for p, perms in self._perms.items():
            for perm in perms:
                out.append((p, perm))
        return out
