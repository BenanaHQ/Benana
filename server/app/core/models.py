from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class Plugin(Base):
    __tablename__ = "plugins"
    id = Column(String(36), primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    version = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_core = Column(Boolean, default=False, nullable=False)
    status = Column(String(20), default="active", nullable=False)  # active/inactive
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class PluginMigration(Base):
    __tablename__ = "plugin_migrations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin = Column(String(255), nullable=False)
    migration_id = Column(String(255), nullable=False)
    checksum = Column(String(128), nullable=False)
    applied_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("plugin", "migration_id", name="uq_plugin_migration"),)


class DummyCore(Base):
    __tablename__ = "dummy_core_table"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
