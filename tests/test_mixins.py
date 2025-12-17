"""Test mixins."""

import unittest

from pydantic import BaseModel
from typing_extensions import Self

import curies
from curies import Converter, Reference
from curies.mixins import (
    SemanticallyProcessable,
    SemanticallyStandardizable,
    process_many,
    standardize_many,
)


class TestMixins(unittest.TestCase):
    """Test mixins."""

    def test_semantically_processable(self) -> None:
        """Test processing."""

        class Processed(BaseModel):
            """A processed model, with a reference."""

            reference: Reference

        class Raw(BaseModel, SemanticallyProcessable[Processed]):
            """A raw model, with a URI."""

            uri: str

            def process(self, converter: Converter) -> Processed:
                """Process the raw model."""
                return Processed(reference=converter.parse(self.uri, strict=True).to_pydantic())

        converter = Converter.from_prefix_map({"GO": "http://purl.obolibrary.org/obo/GO_"})
        initial = Raw(uri="http://purl.obolibrary.org/obo/GO_1234567")
        actual = initial.process(converter)
        self.assertIsInstance(actual, Processed)
        expected = Processed(reference=Reference(prefix="GO", identifier="1234567"))
        self.assertEqual(expected, actual)
        self.assertEqual([expected], process_many([initial], converter))

        # check none handling
        self.assertIsNone(process_many(None, converter))

    def test_standardizable(self) -> None:
        """Test standardizable."""

        class HoldsReference(BaseModel, SemanticallyStandardizable):
            """A test class with a reference."""

            reference: Reference

            def standardize(self, converter: Converter) -> Self:
                """Standardize the reference in the object."""
                return self.model_copy(
                    update={
                        "reference": converter.standardize_reference(self.reference, strict=True),
                    }
                )

        converter = Converter(
            [
                curies.Record(
                    prefix="TEST", prefix_synonyms=["test"], uri_prefix="https://example.org/"
                )
            ]
        )
        initial = HoldsReference(reference=Reference(prefix="test", identifier="1234567"))
        actual = initial.standardize(converter)
        expected = HoldsReference(reference=Reference(prefix="TEST", identifier="1234567"))
        self.assertEqual(expected, actual)
        self.assertEqual([expected], standardize_many([initial], converter))

        # check none handling
        self.assertIsNone(standardize_many(None, converter))
