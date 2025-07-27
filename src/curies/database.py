"""Database adapters for :mod:`curies`.

Using :mod:`sqlmodel`
---------------------
SQLModel is a joint abstraction over :mod:`pydantic` and
:mod:`sqlalchemy`

.. code-block:: python

    from curies import Reference
    from curies.database import get_reference_sa_column
    from sqlmodel import Field, Session, SQLModel, create_engine, select


    class Edge(SQLModel, table=True):
        id: int | None = Field(default=None, primary_key=True)
        subject: Reference = Field(sa_column=get_reference_sa_column())
        predicate: Reference = Field(sa_column=get_reference_sa_column())
        object: Reference = Field(sa_column=get_reference_sa_column())


    e1 = Edge(subject="CHEBI:135122", predicate="skos:exactMatch", object="mesh:C073738")
    e2 = Edge(subject="CHEBI:135125", predicate="skos:exactMatch", object="mesh:C073260")

    engine = create_engine("sqlite://")

    SQLModel.metadata.create_all(engine)

    # Add edges to the database
    with Session(engine) as session:
        session.add_all([e1, e2])
        session.commit()

    # Query for edges with a given subject, by string
    with Session(engine) as session:
        statement = select(Edge).where(Edge.subject == "CHEBI:135122")
        edges = session.exec(statement).all()

    # Query for edges with a given subject, by string
    with Session(engine) as session:
        statement = select(Edge).where(
            Edge.subject == Reference(prefix="CHEBI", identifier="135125")
        )
        edges = session.exec(statement).all()

Using :mod:`sqlalchemy`
-----------------------
SQLAlchemy is a combine high- and mid-level database abstraction
layer and object-relational mapping. It has more opportunities
for configuration over SQLModel.

"""

from typing import Any, ClassVar, Optional

import sqlalchemy
from sqlalchemy import Column
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.orm import Composite, composite
from sqlalchemy.types import TEXT, TypeDecorator

from curies import Reference

__all__ = [
    "SAReferenceTypeDecorator",
    "get_reference_sa_column",
    "get_reference_sa_composite",
]


class SAReferenceTypeDecorator(TypeDecorator[Reference]):
    """A SQLAlchemy type decorator for a :mod:`curies.Reference`."""

    impl = TEXT
    cache_ok: ClassVar[bool] = True  # type:ignore

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
    """Get a SQLAlchemy column with the type decorator for a :mod:`curies.Reference`.

    :param args: positional arguments, passed to :class:`sqlalchemy.Column`
    :param kwargs: keyword arguments, passed to :class:`sqlalchemy.Column`
    :return: A column object, parametrized with :class:`curies.Reference`

    For example, this can be used to model a semantic triple, which has a subject
    reference, predicate reference, and object reference like in the following:

    .. code-block:: python

        from curies import Reference
        from curies.database import get_reference_sa_column
        from sqlmodel import Field, SQLModel


        class Edge(SQLModel, table=True):
            id: int | None = Field(default=None, primary_key=True)
            subject: Reference = Field(sa_column=get_reference_sa_column())
            predicate: Reference = Field(sa_column=get_reference_sa_column())
            object: Reference = Field(sa_column=get_reference_sa_column())
    """
    return sqlalchemy.Column(SAReferenceTypeDecorator(), *args, **kwargs)


class _ReferenceAdapter(Reference):
    """A wrapper for SQLAlchemy for usage in composite()."""

    def __init__(self, prefix: str, identifier: str) -> None:
        """Initialize the SQLAlchemy model."""
        super().__init__(prefix=prefix, identifier=identifier)


def get_reference_sa_composite(
    prefix_column: Column[str], identifier_column: Column[str], *args: Any, **kwargs: Any
) -> Composite[Reference]:
    """Get a composite for a reference.

    :param prefix_column:
    :param identifier_column:
    :param kwargs: keyword arguments passed to :func:`sqlalchemy.orm.composite`
    :returns: A Composite object for a reference

    .. code-block:: python

            from curies import Reference
            from curies.database import get_reference_sa_composite
            from sqlalchemy import Column
            from sqlalchemy.orm import DeclarativeBase


            class Base(DeclarativeBase):
                pass


            class Edge(Base):
                __tablename__ = "edge"

                id = Column(Integer, primary_key=True)

                subject_prefix = Column(String, nullable=False)
                subject_identifier = Column(String, nullable=False)
                predicate_prefix = Column(String, nullable=False)
                predicate_identifier = Column(String, nullable=False)
                object_prefix = Column(String, nullable=False)
                object_identifier = Column(String, nullable=False)

                subject = get_reference_sa_composite(subject_prefix, subject_identifier)
                predicate = get_reference_sa_composite(predicate_prefix, identifier)
                object = get_reference_sa_composite(object_prefix, object_identifier)

    """
    return composite(_ReferenceAdapter, prefix_column, identifier_column, **kwargs)
