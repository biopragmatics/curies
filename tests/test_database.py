"""Tests for database adapters."""

from __future__ import annotations

import unittest

from curies import Prefix, Reference
from curies.database import get_reference_sa_column, get_reference_sa_composite

prefix = Prefix("hero")
id_1 = "1"
id_2 = "2"
id_3 = "3"
name_1 = "Name 1"
name_2 = "Name 2"
name_3 = "Name 3"


class TestDatabase(unittest.TestCase):
    """Tests for database adapters."""

    def test_sqlalchemy(self) -> None:
        """Test SQLalchemy."""
        from sqlalchemy import Column, Integer, String, create_engine
        from sqlalchemy.orm import DeclarativeBase, Session

        class Base(DeclarativeBase):
            """A base."""

        class MyModel(Base):
            """A SQLAlchemy model that uses a reference."""

            __tablename__ = "my_model"

            id = Column(Integer, primary_key=True)
            reference = get_reference_sa_column()
            name = Column(String)

        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)

        model_1 = MyModel(reference=Reference(prefix=prefix, identifier=id_1), name=name_1)
        model_2 = MyModel(reference=Reference(prefix=prefix, identifier=id_2), name=name_2)
        model_3 = MyModel(reference=Reference(prefix=prefix, identifier=id_3), name=name_3)

        with Session(engine) as session:
            session.add(model_1)
            session.add(model_2)
            session.add(model_3)
            session.commit()

        # Test querying with reconstitution
        with Session(engine) as session:
            result = (
                session.query(MyModel)
                .filter(MyModel.reference == Reference(prefix=prefix, identifier=id_1))
                .one()
            )

        self.assertIsInstance(result.reference, Reference)
        self.assertEqual(prefix, result.reference.prefix)
        self.assertEqual(id_1, result.reference.identifier)
        self.assertEqual(name_1, result.name)

    def test_sqlalchemy_composite(self) -> None:
        """Test SQLAlchemy composite models."""
        from sqlalchemy import Column, Integer, String, create_engine
        from sqlalchemy.orm import DeclarativeBase, Session

        class Base(DeclarativeBase):
            """A base."""

        class MyModel(Base):
            """A model for testing composite references."""

            __tablename__ = "my_model"

            id = Column(Integer, primary_key=True)

            reference_prefix = Column(String, nullable=False)
            reference_identifier = Column(String, nullable=False)
            name = Column(String, nullable=False)

            reference = get_reference_sa_composite(reference_prefix, reference_identifier)

        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)

        model_1 = MyModel(reference=Reference(prefix=prefix, identifier=id_1), name=name_1)
        model_2 = MyModel(reference=Reference(prefix=prefix, identifier=id_2), name=name_2)
        model_3 = MyModel(reference=Reference(prefix=prefix, identifier=id_3), name=name_3)

        with Session(engine) as session:
            session.add(model_1)
            session.add(model_2)
            session.add(model_3)
            session.commit()

        # Test querying with reconstitution
        with Session(engine) as session:
            result = (
                session.query(MyModel)
                .filter(MyModel.reference == Reference(prefix=prefix, identifier=id_1))
                .one()
            )

        self.assertIsInstance(result.reference, Reference)
        self.assertEqual(prefix, result.reference.prefix)
        self.assertEqual(id_1, result.reference.identifier)
        self.assertEqual(name_1, result.name)

    def test_sqlmodel(self) -> None:
        """Test SQLModel."""
        from sqlmodel import Field, Session, SQLModel, create_engine, select

        class Model(SQLModel, table=True):
            """A class with a reference."""

            id: int | None = Field(default=None, primary_key=True)
            reference: Reference = Field(sa_column=get_reference_sa_column())
            optional_reference: Reference | None = Field(sa_column=get_reference_sa_column())
            name: str

        model_1 = Model(reference=Reference(prefix=prefix, identifier=id_1), name=name_1)
        model_2 = Model(reference=Reference(prefix=prefix, identifier=id_2), name=name_2)
        model_3 = Model(
            reference=Reference(prefix=prefix, identifier=id_3),
            optional_reference=Reference(prefix=prefix, identifier=id_3),
            name=name_3,
        )

        engine = create_engine("sqlite://")

        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            session.add(model_1)
            session.add(model_2)
            session.add(model_3)
            session.commit()

        # Test querying with reconstitution
        with Session(engine) as session:
            statement = select(Model).where(Model.name == name_2)
            result_1 = session.exec(statement).first()

        if result_1 is None:
            raise TypeError  # this shouldn't be possible
        self.assertIsInstance(result_1.reference, Reference)
        self.assertEqual(prefix, result_1.reference.prefix)
        self.assertEqual(id_2, result_1.reference.identifier)
        self.assertEqual(name_2, result_1.name)

        # Test querying using a string on the reference
        with Session(engine) as session:
            statement = select(Model).where(Model.reference == f"{prefix}:{id_3}")
            result_4 = session.exec(statement).first()

        if result_4 is None:
            raise TypeError  # this shouldn't be possible
        self.assertIsInstance(result_4.reference, Reference)
        self.assertEqual(prefix, result_4.reference.prefix)
        self.assertEqual(id_3, result_4.reference.identifier)
        self.assertEqual(name_3, result_4.name)
        self.assertIsNotNone(result_4.optional_reference)

        # Tests looking up a reference that's missing
        with Session(engine) as session:
            statement = select(Model).where(
                Model.reference == Reference(prefix="nope", identifier="nope")
            )
            self.assertIsNone(session.exec(statement).one_or_none())

        # Tests looking a reference that's there
        with Session(engine) as session:
            statement = select(Model).where(
                Model.reference == Reference(prefix=prefix, identifier=id_1)
            )
            result_3 = session.exec(statement).first()

        if result_3 is None:
            raise TypeError  # this shouldn't be possible
        self.assertIsInstance(result_3.reference, Reference)
        self.assertEqual(prefix, result_3.reference.prefix)
        self.assertEqual(id_1, result_3.reference.identifier)
        self.assertEqual(name_1, result_3.name)
