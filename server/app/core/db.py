from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .settings import Settings


engine = None
SessionLocal: sessionmaker[Session] | None = None


def _dsn(settings: Settings) -> str:
    return (
        f"postgresql+psycopg://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )


def init_engine_and_session(settings: Settings) -> None:
    global engine, SessionLocal
    if engine is None:
        engine = create_engine(_dsn(settings), pool_pre_ping=True, future=True)
        # Avoid attribute expiration on commit so ORM rows can be used after context
        SessionLocal = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            future=True,
        )


@contextmanager
def get_session() -> Iterator[Session]:
    assert SessionLocal is not None, "DB not initialized"
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
