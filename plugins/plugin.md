# Dynamic Plugin Architecture

## Overview

This system implements a dynamic plugin architecture for Python FastAPI applications. Plugins are Python modules that can be loaded dynamically at runtime without requiring server restarts.

## Architecture Components

### Core Components

The system consists of a FastAPI server that manages plugins through a Plugin Manager. The Plugin Manager orchestrates the entire plugin lifecycle including discovery, loading, and route registration. A PostgreSQL database stores plugin metadata and tracks migration states. The system uses SQLAlchemy for database operations and Alembic for core migrations, while plugins provide their own SQL migrations.

Plugin files are organized in the `plugins/` directory with each plugin having its own subdirectory containing `plugin.py`, `routes.py`, and a `migrations/` folder.

## System Flow

### Auto-Discovery Process

When the server starts, it scans the `plugins/` directory for plugin directories. For each directory found, the system validates the plugin structure by checking for `plugin.py` files. If the plugin doesn't exist in the database, it's automatically enabled. If it exists with 'active' status, it's loaded. Plugins with 'inactive' status are skipped even if present on disk.

### Plugin Loading Process

The Plugin Manager imports the plugin module and calls the `get_plugin()` function to obtain a plugin instance. It validates the plugin implements the required `BasePlugin` interface, applies any pending migrations, registers the plugin in the database, calls the plugin's `on_load()` method, registers routes with FastAPI, and registers any declared permissions.

## Plugin Interface

### Required Interface Implementation

Every plugin must implement the `BasePlugin` abstract class, which requires:

- `name`: Plugin identifier
- `version`: Plugin version string
- `description`: Optional description
- `is_core`: Boolean indicating if it's a core plugin
- `migrations_path()`: Static method returning path to migrations directory
- `on_load(ctx)`: Called after migrations but before route registration
- `register_routes(app, router)`: Register FastAPI routes
- `register_permissions()`: Optional method returning list of permissions
- `seed(db)`: Optional method for database seeding
- `on_unload(ctx)`: Optional cleanup method

### Example Plugin Implementation

```python
from pathlib import Path
from typing import Any
from fastapi import FastAPI, APIRouter
from server.app.core.plugin_spi import BasePlugin, Permission

class MyPlugin(BasePlugin):
    name = "myplugin"
    version = "1.0.0"
    description = "My awesome plugin"
    is_core = False

    @staticmethod
    def migrations_path() -> Path:
        return Path(__file__).parent / "migrations"

    def on_load(self, ctx: dict[str, Any]) -> None:
        services = ctx.get("services")
        services.register("myplugin.echo", lambda x: x)

    def register_routes(self, app: FastAPI, router: APIRouter) -> None:
        @router.get("/hello")
        def hello():
            return {"message": "Hello from MyPlugin!"}

        @router.post("/echo")
        def echo(data: dict):
            return {"received": data}

    def register_permissions(self):
        return [
            Permission(key="myplugin:view", description="View myplugin"),
            Permission(key="myplugin:edit", description="Edit myplugin"),
        ]

    def seed(self, db) -> None:
        # Optional database seeding
        pass

    def on_unload(self, ctx: dict[str, Any]) -> None:
        # Optional cleanup
        pass

def get_plugin() -> BasePlugin:
    return MyPlugin()
```

## Database Schema

The system uses three main tables. The `plugins` table stores core plugin information including id, name, version, description, core status, and timestamps. The `plugin_migrations` table tracks which migrations have been applied for each plugin. The `dummy_core_table` is a placeholder for core functionality.

```sql
CREATE TABLE plugins (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    version VARCHAR(100) NOT NULL,
    description TEXT,
    is_core BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE plugin_migrations (
    id SERIAL PRIMARY KEY,
    plugin VARCHAR(255) NOT NULL,
    migration_id VARCHAR(255) NOT NULL,
    checksum VARCHAR(128) NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(plugin, migration_id)
);
```

## API Endpoints

The system provides RESTful API endpoints for plugin management under `/admin/`:

- `GET /admin/plugins` - List available and loaded plugins
- `POST /admin/plugins/{name}/enable` - Enable a plugin
- `POST /admin/plugins/{name}/disable` - Disable a plugin  
- `POST /admin/plugins/{name}/reload` - Reload a plugin
- `POST /admin/plugins/install` - Install a plugin from ZIP upload

### API Examples

#### List All Plugins
```bash
curl http://localhost:8000/admin/plugins
```

```json
{
  "available": ["powertable", "reports"],
  "loaded": ["powertable"]
}
```

#### Enable Plugin
```bash
curl -X POST http://localhost:8000/admin/plugins/reports/enable
```

```json
{
  "status": "enabled",
  "name": "reports"
}
```

#### Reload Plugin
```bash
curl -X POST http://localhost:8000/admin/plugins/powertable/reload
```

```json
{
  "status": "reloaded", 
  "name": "powertable"
}
```

## Plugin Development Guide

Creating a new plugin involves several steps:

### Step-by-Step Process

#### 1. Create Plugin Directory
```bash
mkdir plugins/myplugin
cd plugins/myplugin
```

#### 2. Create Plugin Files
Create `plugin.py` with the required interface implementation (see example above).

#### 3. Create Routes
Create `routes.py` for route definitions:

```python
from fastapi import APIRouter

def get_router() -> APIRouter:
    r = APIRouter()

    @r.get("/hello")
    def hello():
        return {"plugin": "myplugin", "message": "Hello!"}

    return r
```

#### 4. Add Migrations (Optional)
Create `migrations/` directory and add SQL migration files:

```sql
-- migrations/0001_init.sql
CREATE TABLE IF NOT EXISTS myplugin_items (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

#### 5. Test Plugin
Start the server - your plugin will be auto-discovered and loaded:
```bash
cd server
uvicorn app.main:app --reload
```

#### 6. Verify Plugin
```bash
curl http://localhost:8000/admin/plugins  # Check registration
curl http://localhost:8000/myplugin/hello  # Test plugin endpoint
```

## Key Features

- **Auto-Discovery**: Plugins are automatically found in `plugins/` directory
- **Dynamic Loading**: Python modules loaded at runtime without compilation
- **Interface Validation**: Plugins must implement `BasePlugin` interface
- **Hot Reload**: Plugins can be reloaded without server restart
- **Database Integration**: Plugin metadata stored in PostgreSQL
- **Migration Support**: Plugins can provide SQL migrations
- **Permission System**: Built-in permission registration
- **Service Registry**: Plugins can register and use services
- **Route Management**: Plugin routes automatically registered with FastAPI

### Feature Summary

- **Auto-Discovery**: Plugins automatically found in `plugins/` directory
- **Dynamic Loading**: Python modules loaded at runtime
- **Interface Validation**: Plugins must implement `BasePlugin`
- **Hot Reload**: Plugins can be reloaded without server restart
- **Database Integration**: Plugin metadata stored in PostgreSQL
- **Migration Support**: SQL migrations per plugin
- **Permission System**: Declarative permission registration
- **Service Registry**: Shared service registration
- **Route Management**: Automatic FastAPI route registration
