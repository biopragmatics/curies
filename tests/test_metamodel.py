"""Test the lightweight metadata model."""

import unittest

from pydantic import BaseModel

from curies import NamableReference
from curies.metamodel import from_records


class TestModel(unittest.TestCase):
    """Test parsing models."""

    def test_model(self) -> None:
        """Test parsing into a namable reference."""

        class MM(BaseModel):
            """Test model."""

            curie: NamableReference

        names = {"curie": "curie_label"}
        records = [
            {"curie": "GO:0000001", "curie_label": "Test 1"},
            {"curie": "GO:0000002", "curie_label": "Test 2"},
        ]

        models = list(from_records(records, MM, names=names))
        self.assertEqual(
            [
                MM(curie=NamableReference(prefix="GO", identifier="0000001", name="Test 1")),
                MM(curie=NamableReference(prefix="GO", identifier="0000002", name="Test 2")),
            ],
            models,
        )
