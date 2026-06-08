"""Async SQLAlchemy engine and session. SQLite in dev, Postgres in prod."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create the tables if missing (dev). In prod: use Alembic instead."""
    from app.db import models  # noqa: F401  (registers the models)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
