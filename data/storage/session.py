"""Database factory kept separate so local no-provider mode needs no DB driver."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

from data.storage.models import Base


def make_engine(database_url: str) -> Engine:
    return create_engine(database_url, future=True)


def create_schema(database_url: str) -> None:
    engine = make_engine(database_url)
    Base.metadata.create_all(engine)
