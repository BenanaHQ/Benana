from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from datetime import datetime
import uuid
from pathlib import Path
from typing import Dict, Optional
import logging as _logging
from fastapi import FastAPI, APIRouter

from .settings import get_settings, Settings
from .service_registry import ServiceRegistry
from .plugin_spi import BasePlugin
from .migrator import apply_plugin_migrations
from .db import get_session
from .models import Plugin as PluginModel
from .permissions import PermissionRegistry


@dataclass
class LoadedPlugin:
    plugin: BasePlugin
    module_name: str
    router: APIRouter


class PluginManager:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        # Resolve plugins_dir with sensible fallbacks so running from `server/` works
        configured = Path(self.settings.plugins_dir)
        candidates = [
            configured,
            Path.cwd() / configured,
            Path.cwd().parent / configured,
        ]
        self.plugins_dir = next(
            (c for c in candidates if c.exists() and c.is_dir()), configured
        )
        self.registry = ServiceRegistry()
        self.permissions = PermissionRegistry()
        self.loaded: Dict[str, LoadedPlugin] = {}

    def startup(self, app: FastAPI) -> None:
        # Ensure 'plugins' namespace is importable
        # Ensure parent of plugins_dir is on sys.path so `import plugins.*` works
        parent = self.plugins_dir.resolve().parent
        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))
        self.app = app
        # Autoload any plugins recorded as active in DB
        try:
            self.autoload_active()
        except Exception as e:
            # avoid failing app startup entirely; log and continue
            # TODO: implement proper error handling
            import logging

            logging.getLogger(__name__).warning("Autoload failed: %s", e)

    def shutdown(self) -> None:
        for name in list(self.loaded.keys()):
            self.unload(name)

    def autoload_active(self) -> None:
        """Autoload plugins at startup.

        Rules:
        - Any plugin present on disk (plugins/<name>/plugin.py) is enabled by default
          if no prior DB record exists.
        - Plugins with DB status='active' are loaded (if folder exists).
        - Plugins with DB status='inactive' are skipped even if present on disk.
        - If DB marks active but folder is missing, log a warning and skip.
        """

        # Current DB states
        with get_session() as s:
            rows = s.query(PluginModel.name, PluginModel.status).all()
            states = {name: status for (name, status) in rows}

        discovered = set(self.discover())

        # Load discovered plugins that are either new (no DB record) or marked active
        for name in sorted(discovered):
            status = states.get(name)
            if status is None or status == "active":
                try:
                    self.load(name)
                except Exception as exc:
                    _logging.getLogger(__name__).error(
                        "Failed to autoload plugin '%s': %s", name, exc
                    )
            else:
                _logging.getLogger(__name__).info(
                    "Plugin '%s' present on disk but DB status is '%s'; skipping",
                    name,
                    status,
                )

        # Warn about DB-active plugins whose folders are missing
        for name, status in states.items():
            if status == "active" and name not in discovered:
                _logging.getLogger(__name__).warning(
                    "Active plugin '%s' not found on disk; skipping", name
                )

    def discover(self) -> list[str]:
        if not self.plugins_dir.exists():
            return []
        names = []
        for p in self.plugins_dir.iterdir():
            if p.is_dir() and (p / "plugin.py").exists():
                names.append(p.name)
        return names

    def load(self, name: str) -> None:
        if name in self.loaded:
            return
        module_name = f"plugins.{name}.plugin"
        mod = importlib.import_module(module_name)
        if not hasattr(mod, "get_plugin"):
            raise RuntimeError(f"Plugin {name} missing get_plugin()")
        plugin: BasePlugin = mod.get_plugin()

        # Apply per-plugin migrations
        migrations_dir = plugin.migrations_path()
        apply_plugin_migrations(plugin.name, migrations_dir)

        # Ensure plugin record exists/updated
        with get_session() as s:
            row = s.query(PluginModel).filter_by(name=plugin.name).one_or_none()
            now = datetime.utcnow()
            if row is None:
                row = PluginModel(
                    id=str(uuid.uuid4()),
                    name=plugin.name,
                    version=plugin.version,
                    description=getattr(plugin, "description", ""),
                    is_core=getattr(plugin, "is_core", False),
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
                s.add(row)
            else:
                row.version = plugin.version
                row.description = getattr(plugin, "description", row.description)
                row.is_core = getattr(plugin, "is_core", row.is_core)
                row.status = "active"
                row.updated_at = now

        # on_load
        plugin.on_load({"services": self.registry, "permissions": self.permissions})

        # Register routes
        router = APIRouter()
        plugin.register_routes(self.app, router)
        self.app.include_router(router, prefix=f"/{name}", tags=[name])

        # Register declared permissions
        self.permissions.register(plugin.name, plugin.register_permissions())

        # Seed (optional)
        with get_session() as s:
            try:
                plugin.seed(s)
            except Exception:
                # seeding is optional; do not fail plugin load for seed errors
                s.rollback()

        self.loaded[name] = LoadedPlugin(
            plugin=plugin, module_name=module_name, router=router
        )

    def unload(self, name: str) -> None:
        lp = self.loaded.get(name)
        if not lp:
            return
        try:
            lp.plugin.on_unload(
                {"services": self.registry, "permissions": self.permissions}
            )
        finally:
            # TODO: No way to de-register routes in FastAPI; for now removing from
            # loaded registry only, not mutating DB status here; need to check if
            # there is a better way to do this
            self.loaded.pop(name, None)

    def disable(self, name: str) -> None:
        """Explicitly inactivate a plugin: set DB status and unload runtime state."""
        with get_session() as s:
            row = s.query(PluginModel).filter_by(name=name).one_or_none()
            if row is not None:
                row.status = "inactive"
        self.unload(name)

    def reload(self, name: str) -> None:
        lp = self.loaded.get(name)
        module_name = lp.module_name if lp else f"plugins.{name}.plugin"
        self.unload(name)
        if module_name in sys.modules:
            del sys.modules[module_name]
        self.load(name)
