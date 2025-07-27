"""Tests for database adapters."""

import unittest

from curies import Reference
from curies.database import get_reference_sa_column


class TestDatabase(unittest.TestCase):
    """Tests for database adapters."""

    def test_sqlalchemy(self) -> None:
        """Test SQLalchemy."""

    def test_sqlmodel(self) -> None:
        """Test SQLModel."""
        from sqlmodel import Field, Session, SQLModel, create_engine, select

        class Hero(SQLModel, table=True):
            """A class with a reference."""

            id: int | None = Field(default=None, primary_key=True)
            reference: Reference = Field(sa_column=get_reference_sa_column())
            name: str

        hero_1 = Hero(reference=Reference(prefix="hero", identifier="1"), name="Deadpond")
        hero_2 = Hero(reference=Reference(prefix="hero", identifier="2"), name="Spider-Boy")
        hero_3 = Hero(reference=Reference(prefix="hero", identifier="3"), name="Rusty-Man")

        engine = create_engine("sqlite://")

        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            session.add(hero_1)
            session.add(hero_2)
            session.add(hero_3)
            session.commit()

        with Session(engine) as session:
            statement = select(Hero).where(Hero.name == "Spider-Boy")
            hero = session.exec(statement).first()

        self.assertIsInstance(hero.reference, Reference)
        self.assertEqual("hero", hero.reference.prefix)
        self.assertEqual("1", hero.reference.identifier)
        self.assertEqual("Pedro Parqueador", hero.secret_name)
