from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.openapi.utils import get_openapi

from .core.settings import get_settings
from .core.db import init_engine_and_session
from .core.migrator import bootstrap, run_host_migrations
from .core.plugin_manager import PluginManager
from .api.plugin_management import router as admin_router


app = FastAPI(
    default_response_class=ORJSONResponse,
    title="Benana Host Runtime",
    version="0.1.0",
    description=(
        "Benana FastAPI host runtime with dynamic plugins. "
        "Host uses Alembic for core migrations; plugins provide SQL migrations and routes."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    tags = openapi_schema.setdefault("tags", [])
    core_tags = {t.get("name") for t in tags}
    for t in (
        {"name": "plugin", "description": "Plugin management APIs"},
        {"name": "health", "description": "Health and readiness"},
    ):
        if t["name"] not in core_tags:
            tags.append(t)
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore


@app.on_event("startup")
def on_startup():
    settings = get_settings()

    # Initialize DB engine/session
    init_engine_and_session(settings)

    # Run host migrations (Alembic) first, then ensure bootstrap tables (for plugin tracking)
    run_host_migrations(upgrade=True)
    bootstrap()

    # Initialize plugin manager and load active/core plugins later
    app.state.plugin_manager = PluginManager(settings=settings)
    app.state.plugin_manager.startup(app)


@app.on_event("shutdown")
def on_shutdown():
    pm: PluginManager = app.state.plugin_manager
    pm.shutdown()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(admin_router, prefix="/admin", tags=["admin"])
