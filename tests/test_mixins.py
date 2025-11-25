"""Test mixins."""

import unittest

from pydantic import BaseModel

from curies import Converter, Reference
from curies.mixins import SemanticallyProcessable, ReverseSemanticallyProcessable, X


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

    def test_reversesemantically_processable(self) -> None:
        """Test processing."""

        class Raw(BaseModel):
            """A raw model, with a URI."""

            uri: str

        class Processed(BaseModel, ReverseSemanticallyProcessable[Raw]):
            """A processed model, with a reference."""

            reference: Reference

            def unprocess(self, converter: Converter) -> Raw:
                return Raw(uri=converter.expand_reference(self.reference, strict=True))

        c = Converter.from_prefix_map({"GO": "http://purl.obolibrary.org/obo/GO_"})

        p = Processed(reference=Reference(prefix="GO", identifier="1234567"))
        r = p.unprocess(c)
        self.assertEqual("http://purl.obolibrary.org/obo/GO_1234567", r.uri)
