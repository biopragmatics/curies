"""Database adapters for :mod:`curies`."""

from typing import Any, Optional

import sqlalchemy
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TEXT, TypeDecorator

from curies import Reference

__all__ = [
    "ReferenceType",
    "get_reference_sa_column",
]


class ReferenceType(TypeDecorator[Reference]):
    """A SQLAlchemy type decorator for a :mod:`curies.Reference`."""

    impl = TEXT
    cache_ok: bool = True  # for SQLAlchemy's caching system

    def process_bind_param(self, value: str | Reference | None, dialect: Dialect) -> Optional[str]:
        """Convert the Python object into a database value."""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return value.curie

    def process_result_value(self, value: Optional[str], dialect: Dialect) -> Optional[Reference]:
        """Convert the database value into a Python object."""
        if value is None:
            return None
        return Reference.from_curie(value)

    # TODO what about process literal param?


def get_reference_sa_column(*args: Any, **kwargs: Any) -> sqlalchemy.Column[Reference]:
    """Get a SQLAlchemy column with the type decorator for a :mod:`curies.Reference`."""
    return sqlalchemy.Column(ReferenceType(), *args, **kwargs)
