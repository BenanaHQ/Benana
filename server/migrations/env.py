from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Interpret the config file for Python logging.
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use app settings to build the URL at runtime
try:
    from app.core.settings import get_settings
except Exception:
    get_settings = None  # type: ignore

def _dsn():
    if get_settings is None:
        # fallback to env vars if app import fails
        user = os.getenv("BENANA_DB_USER", "benana_user")
        pwd = os.getenv("BENANA_DB_PASSWORD", "benana_password")
        host = os.getenv("BENANA_DB_HOST", "localhost")
        port = os.getenv("BENANA_DB_PORT", "5432")
        name = os.getenv("BENANA_DB_NAME", "benana")
    else:
        s = get_settings()
        user, pwd, host, port, name = s.db_user, s.db_password, s.db_host, str(s.db_port), s.db_name
    return f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{name}"

config.set_main_option("sqlalchemy.url", _dsn())

# We don't use autogenerate now: create manual revisions.
target_metadata = None

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

