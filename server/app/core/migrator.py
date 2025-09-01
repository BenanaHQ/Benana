from __future__ import annotations

from __future__ import annotations

import hashlib
from pathlib import Path
import logging
from typing import Iterable, List

from sqlalchemy import text, select

from . import db as _db
from .models import Base, PluginMigration, Plugin as PluginModel
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command
from pathlib import Path as _Path


def bootstrap() -> None:
    """Create host tables if not present."""
    assert _db.engine is not None, "DB engine not initialized"
    # Only ensure tracking tables for plugins exist here; core tables are Alembic-managed
    PluginModel.__table__.create(bind=_db.engine, checkfirst=True)
    PluginMigration.__table__.create(bind=_db.engine, checkfirst=True)


def apply_sql_batch(sql: str) -> None:
    assert _db.engine is not None
    with _db.engine.begin() as conn:
        conn.execute(text(sql))


def run_host_migrations(upgrade: bool = True) -> None:
    """Run Alembic upgrade head for host migrations when enabled.

    This is intended for dev; in prod, prefer running Alembic via CI/CD.
    """
    cfg_path = _Path(__file__).resolve().parents[2] / "alembic.ini"
    if not cfg_path.exists():
        logging.getLogger(__name__).info(
            "Alembic config not found at %s; skipping", cfg_path
        )
        return
    cfg = AlembicConfig(str(cfg_path))
    if upgrade:
        logging.getLogger(__name__).info("Running host migrations: upgrade head")
        alembic_command.upgrade(cfg, "head")


def _checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _list_sql_files(path: Path) -> list[Path]:
    if not path.exists() or not path.is_dir():
        return []
    return sorted(
        [p for p in path.iterdir() if p.suffix.lower() == ".sql" and p.is_file()]
    )


def _is_down_file(path: Path) -> bool:
    # convention: 0001_xxx.down.sql
    return path.name.endswith(".down.sql")


def _migration_id_from_path(path: Path) -> str:
    # strip .sql and optional .down suffix
    stem = path.stem  # e.g., 0001_init or 0001_init.down
    if stem.endswith(".down"):
        stem = stem[: -len(".down")]
    return stem


def get_applied_migrations(plugin_name: str) -> dict[str, str]:
    """Return mapping of migration_id -> checksum for a plugin."""
    with _db.get_session() as s:
        rows: Iterable[PluginMigration] = s.execute(
            select(PluginMigration).where(PluginMigration.plugin == plugin_name)
        ).scalars()
        return {r.migration_id: r.checksum for r in rows}


def apply_plugin_migrations(plugin_name: str, migrations_dir: Path) -> None:
    """Apply all pending .sql migrations for a plugin in a single transaction.

    - Skips `.down.sql` files (reserved for rollbacks).
    - Validates checksum drift before applying.
    - Executes DDL and inserts tracking rows atomically.
    """
    files = _list_sql_files(migrations_dir)
    if not files:
        return

    applied = get_applied_migrations(plugin_name)

    # list of pending migrations (id, sql, checksum) and pre-check drift
    pending: list[tuple[str, str, str]] = []
    for f in files:
        if _is_down_file(f):
            continue
        mig_id = _migration_id_from_path(f)
        data = f.read_bytes()
        cs = _checksum(data)
        prev = applied.get(mig_id)
        if prev is not None:
            if prev != cs:
                raise RuntimeError(
                    f"Checksum mismatch for {plugin_name}:{mig_id} (drift detected)"
                )
            continue  # already applied
        pending.append((mig_id, data.decode("utf-8"), cs))

    if not pending:
        logging.getLogger(__name__).info(
            "Migrations: no pending files for plugin '%s'", plugin_name
        )
        return

    # apply all pending migrations in a single transaction
    assert _db.engine is not None
    logging.getLogger(__name__).info(
        "Applying migrations for plugin '%s': %s",
        plugin_name,
        ", ".join(m for m, _, _ in pending),
    )
    with _db.engine.begin() as conn:
        for mig_id, sql, _ in pending:
            conn.execute(text(sql))
        # Record applied migrations within the same transaction
        for mig_id, _sql, cs in pending:
            conn.execute(
                text(
                    """
                    INSERT INTO plugin_migrations (plugin, migration_id, checksum, applied_at)
                    VALUES (:p, :m, :c, CURRENT_TIMESTAMP)
                    """
                ),
                {"p": plugin_name, "m": mig_id, "c": cs},
            )


def list_applied(plugin_name: str) -> List[PluginMigration]:
    with _db.get_session() as s:
        rows: Iterable[PluginMigration] = s.execute(
            select(PluginMigration)
            .where(PluginMigration.plugin == plugin_name)
            .order_by(PluginMigration.applied_at.desc())
        ).scalars()
        return list(rows)


def rollback_plugin_migrations(
    plugin_name: str, migrations_dir: Path, steps: int = 1
) -> list[str]:
    """Rollback the last N applied migrations for a plugin by running corresponding .down.sql files.

    Each rollback is executed in its own transaction; on success, the migration record is removed.
    """
    if steps <= 0:
        return []
    applied_rows = list_applied(plugin_name)
    to_rollback = applied_rows[:steps]
    rolled: list[str] = []
    if not to_rollback:
        logging.getLogger(__name__).info(
            "Rollback: no applied migrations to rollback for plugin '%s'", plugin_name
        )
        return []

        logging.getLogger(__name__).info(
            "Rolling back last %d migrations for plugin '%s': %s",
            len(to_rollback),
            plugin_name,
            ", ".join(r.migration_id for r in to_rollback),
        )

    for row in to_rollback:
        mig_id = row.migration_id
        down_file = migrations_dir / f"{mig_id}.down.sql"
        if not down_file.exists():
            raise RuntimeError(
                f"Down migration not found for {plugin_name}:{mig_id} -> {down_file.name}"
            )
        sql = down_file.read_text(encoding="utf-8")
        assert _db.engine is not None
        with _db.engine.begin() as conn:
            conn.execute(text(sql))
            with _db.get_session() as s:
                # remove record
                rec = s.get(PluginMigration, row.id)
                if rec is not None:
                    s.delete(rec)
        rolled.append(mig_id)
    return rolled
