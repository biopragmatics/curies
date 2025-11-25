"""Test mixins."""

import unittest
from typing import Self

from pydantic import BaseModel

import curies
from curies import Converter, Reference
from curies.mixins import SemanticallyProcessable, Standardizable


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

        c = Converter.from_prefix_map({"GO": "http://purl.obolibrary.org/obo/GO_"})
        v = Raw(uri="http://purl.obolibrary.org/obo/GO_1234567")
        p = v.process(c)
        self.assertIsInstance(p, Processed)
        self.assertEqual(Reference(prefix="GO", identifier="1234567"), p.reference)

    def test_standardizable(self) -> None:
        """Test standardizable."""

        class HoldsReference(BaseModel, Standardizable):
            reference: Reference

            def standardize(self, converter: Converter) -> Self:
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
        init = HoldsReference(reference=Reference(prefix="test", identifier="1234567"))
        end = init.standardize(converter)
        self.assertEqual(Reference(prefix="TEST", identifier="1234567"), end.reference)
