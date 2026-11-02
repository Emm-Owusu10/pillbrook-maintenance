"""Database foundation: the shared model base class, an engine builder, and the request dependency."""
from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session

# Predictable constraint names make later migrations clean and reviewable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def make_engine(database_url: str) -> Engine:
    # pool_pre_ping tests a connection before use, so a restarted database does not cause errors.
    return create_engine(database_url, pool_pre_ping=True)


def get_db(request: Request) -> Iterator[Session]:
    """One database session per request, closed afterwards."""
    factory = request.app.state.session_factory
    if factory is None:
        raise RuntimeError("No database is configured for this application.")
    with factory() as session:
        yield session