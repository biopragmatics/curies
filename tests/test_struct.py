"""Tests for the structure."""

from __future__ import annotations

import unittest

from pydantic import ValidationError

import curies
from curies.api import (
    Converter,
    NamableReference,
    NamedReference,
    Records,
    Reference,
    ReferenceTuple,
)
from curies.utils import NoCURIEDelimiterError

CHEBI_URI_PREFIX = "http://purl.obolibrary.org/obo/CHEBI_"


class TestStruct(unittest.TestCase):
    """Test the data structures."""

    def test_not_curie(self) -> None:
        """Test a malformed CURIE."""
        with self.assertRaises(NoCURIEDelimiterError) as e:
            Reference.from_curie("not a curie")
        self.assertIn("does not appear to be a CURIE", str(e.exception))

    def test_default_prefix(self) -> None:
        """Test a default (empty) prefix."""
        ref = Reference.from_curie(":something")
        self.assertEqual("", ref.prefix)
        self.assertEqual("something", ref.identifier)

    def test_default_identifier(self) -> None:
        """Test a default (empty) identifier."""
        ref = Reference.from_curie("p1:")
        self.assertEqual("p1", ref.prefix)
        self.assertEqual("", ref.identifier)

    def test_multiple_delimiters(self) -> None:
        """Test a default (empty) identifier."""
        ref = Reference.from_curie("a1:b2:c3")
        self.assertEqual("a1", ref.prefix)
        self.assertEqual("b2:c3", ref.identifier)

    def test_records(self) -> None:
        """Test a list of records."""
        records = Records.model_validate([{"prefix": "chebi", "uri_prefix": CHEBI_URI_PREFIX}])
        converter = Converter(records=records)
        self.assertEqual({"chebi"}, converter.get_prefixes())

    def test_sort(self) -> None:
        """Test sorting."""
        start = [
            Reference.from_curie("def:1234"),
            Reference.from_curie("abc:1234"),
            Reference.from_curie("abc:1235"),
        ]
        expected = [
            Reference.from_curie("abc:1234"),
            Reference.from_curie("abc:1235"),
            Reference.from_curie("def:1234"),
        ]
        self.assertEqual(expected, sorted(start))

    def test_set_membership(self) -> None:
        """Test membership in sets."""
        collection = {
            Reference.from_curie("def:1234"),
            Reference.from_curie("abc:1234"),
            Reference.from_curie("abc:1235"),
        }
        self.assertIn(Reference.from_curie("def:1234"), collection)
        self.assertNotIn(Reference.from_curie("xyz:1234"), collection)
        self.assertNotIn(Reference.from_curie(":1234"), collection)
        self.assertNotIn(Reference.from_curie("abc:"), collection)

    def test_named_set_membership(self) -> None:
        """Test membership in sets of named references."""
        references = {
            NamedReference.from_curie("a:1", "name1"),
            NamedReference.from_curie("a:2", "name2"),
        }
        self.assertIn(Reference.from_curie("a:1"), references)
        self.assertIn(NamableReference.from_curie("a:1"), references)
        self.assertIn(NamedReference.from_curie("a:1", "name1"), references)
        self.assertIn(NamableReference.from_curie("a:1", "name1"), references)
        # the following is a weird case, but shows how this works
        self.assertIn(NamedReference.from_curie("a:1", "name2"), references)

        references_2 = {
            Reference.from_curie("a:1"),
            Reference.from_curie("a:2"),
        }
        self.assertIn(Reference.from_curie("a:1"), references_2)
        self.assertIn(NamableReference.from_curie("a:1", "name1"), references_2)
        self.assertIn(NamedReference.from_curie("a:1", "name1"), references_2)

    def test_tuple(self) -> None:
        """Test reference tuples."""
        t = ReferenceTuple.from_curie("a:1")
        self.assertEqual(Reference(prefix="a", identifier="1"), t.to_pydantic())
        self.assertEqual(
            NamedReference(prefix="a", identifier="1", name="name"), t.to_pydantic(name="name")
        )
        with self.assertRaises(ValueError):
            t.to_pydantic(name="")

    def test_reference_constructor(self) -> None:
        """Test constructing a reference."""
        r1 = Reference(prefix="a", identifier="1")
        r2 = NamableReference(prefix="a", identifier="2")
        r3 = NamableReference(prefix="a", identifier="3", name="item 3")
        r4 = NamedReference(prefix="a", identifier="4", name="item 4")

        self.assertEqual(Reference(prefix="a", identifier="1"), Reference.from_reference(r1))
        self.assertEqual(Reference(prefix="a", identifier="2"), Reference.from_reference(r2))
        self.assertEqual(Reference(prefix="a", identifier="3"), Reference.from_reference(r3))
        self.assertEqual(Reference(prefix="a", identifier="4"), Reference.from_reference(r4))

        self.assertEqual(
            NamableReference(prefix="a", identifier="1", name=None),
            NamableReference.from_reference(r1),
        )
        self.assertEqual(
            NamableReference(prefix="a", identifier="2", name=None),
            NamableReference.from_reference(r2),
        )
        self.assertEqual(
            NamableReference(prefix="a", identifier="3", name="item 3"),
            NamableReference.from_reference(r3),
        )
        self.assertEqual(
            NamableReference(prefix="a", identifier="4", name="item 4"),
            NamableReference.from_reference(r4),
        )

        with self.assertRaises(TypeError):
            NamedReference.from_reference(r1)
        with self.assertRaises(ValidationError):
            NamedReference.from_reference(r2)
        self.assertEqual(
            NamedReference(prefix="a", identifier="3", name="item 3"),
            NamedReference.from_reference(r3),
        )
        self.assertEqual(
            NamedReference(prefix="a", identifier="4", name="item 4"),
            NamedReference.from_reference(r4),
        )

    def test_without_name(self) -> None:
        """Test removing names."""
        c1 = Reference.from_curie("a:1")
        c2 = NamableReference.from_curie("a:1")
        c3 = NamableReference.from_curie("a:1", name="test")
        c4 = NamedReference.from_curie("a:1", name="test")

        for reference in [c1, c2, c3, c4]:
            new = reference.without_name()
            self.assertIsInstance(new, Reference)
            self.assertNotIsInstance(new, NamableReference)

    def test_with_name(self) -> None:
        """Test with name."""
        r1 = curies.Reference.from_curie("chebi:1234")
        r2 = r1.with_name("test")
        self.assertIsInstance(r2, NamedReference)
        r3 = r2.without_name()
        self.assertIsInstance(r3, Reference)
        self.assertNotIsInstance(r3, NamableReference)
