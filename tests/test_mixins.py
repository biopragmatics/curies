"""Test mixins."""

import unittest

from pydantic import BaseModel

from curies import Converter, Reference
from curies.mixins import SemanticallyProcessable


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
