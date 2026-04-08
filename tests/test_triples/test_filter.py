"""Test filter functions."""

import unittest
from collections.abc import Iterable

from curies import Converter, Reference, Triple
from curies.triples import (
    exclude_object_prefixes,
    exclude_prefixes,
    exclude_references,
    exclude_same_prefixes,
    exclude_subject_prefixes,
    exclude_triples,
    keep_object_prefixes,
    keep_prefixes,
    keep_references_both,
    keep_references_either,
    keep_subject_prefixes,
    keep_triples_by_hash,
)
from curies.vocabulary import exact_match, subclass_of

c1, c2, c3, c4 = "DOID:0050577", "mesh:C562966", "umls:C4551571", "DOID:225"
r1, r2, r3, r4 = (Reference.from_curie(c) for c in [c1, c2, c3, c4])
m1 = Triple.from_curies(c1, exact_match.curie, c2)
m2 = Triple.from_curies(c2, exact_match.curie, c3)
m3 = Triple.from_curies(c1, exact_match.curie, c3)
m4 = Triple.from_curies(c1, subclass_of.curie, c4)
M123 = [m1, m2, m3]
converter = Converter.from_prefix_map(
    {
        "DOID": "http://purl.obolibrary.org/obo/DOID_",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "mesh": "http://id.nlm.nih.gov/mesh/",
        "umls": "https://uts.nlm.nih.gov/uts/umls/concept/",
    }
)


def _x(triples: Iterable[Triple]) -> str:
    return ", ".join("-".join(e.as_str_triple()) for e in triples)


class TestFilters(unittest.TestCase):
    """Test filters."""

    def assert_triple_lists(self, expected: list[Triple], actual: Iterable[Triple]) -> None:
        """Test two triple lists are the same."""
        actual = list(actual)
        self.assertEqual(expected, actual, msg=f"\nExpected: {_x(expected)}\nActual: {_x(actual)}")

    def test_exclude_object_prefixes(self) -> None:
        """Test excluding object prefixes."""
        self.assert_triple_lists([m1], exclude_object_prefixes(M123, {"umls"}))
        self.assert_triple_lists([m2, m3], exclude_object_prefixes(M123, {"mesh"}))
        self.assert_triple_lists(M123, exclude_object_prefixes(M123, {"DOID"}))

    def test_exclude_prefixes(self) -> None:
        """Test excluding prefixes."""
        self.assert_triple_lists([m1], exclude_prefixes(M123, {"umls"}))
        self.assert_triple_lists([m2], exclude_prefixes(M123, {"DOID"}))
        self.assert_triple_lists([m3], exclude_prefixes(M123, {"mesh"}))

    def test_exclude_subject_prefixes(self) -> None:
        """Test excluding subject prefixes."""
        self.assert_triple_lists([m2], exclude_subject_prefixes(M123, {"DOID"}))
        self.assert_triple_lists(M123, exclude_subject_prefixes(M123, {"umls"}))
        self.assert_triple_lists([m1, m3], exclude_subject_prefixes(M123, {"mesh"}))

    def test_exclude_same_prefixes(self) -> None:
        """Test excluding same prefixes."""
        self.assert_triple_lists(M123, exclude_same_prefixes([m1, m2, m3, m4]))

    def test_exclude_triples(self) -> None:
        """Test excluding triples."""
        self.assert_triple_lists([m1, m2], exclude_triples(M123, m3))
        self.assert_triple_lists([m1, m2], exclude_triples(M123, [m3]))

    def test_keep_object_prefixes(self) -> None:
        """Test keeping object prefixes."""
        self.assert_triple_lists([m2, m3], keep_object_prefixes(M123, {"umls"}))

    def test_keep_prefixes(self) -> None:
        """Test keeping prefixes."""
        self.assert_triple_lists([], keep_prefixes(M123, {"NOPE", "also nope"}))
        self.assert_triple_lists([m1], keep_prefixes(M123, {"DOID", "mesh"}))
        self.assert_triple_lists([m1], keep_prefixes(M123, {"DOID", "umls"}))
        self.assert_triple_lists([m1], keep_prefixes(M123, {"mesh", "umls"}))
        self.assert_triple_lists(M123, keep_prefixes(M123, {"DOID", "umls", "mesh"}))

    def test_keep_subject_prefixes(self) -> None:
        """Test keeping subject prefixes."""
        self.assert_triple_lists([m1, m3], keep_subject_prefixes(M123, {"DOID"}))

    def test_keep_triple_by_hash(self) -> None:
        """Test keeping triples by hash."""
        self.assert_triple_lists(
            [m1], keep_triples_by_hash(M123, converter, converter.hash_triple(m1))
        )
        self.assert_triple_lists(
            [m1, m2],
            keep_triples_by_hash(
                M123, converter, [converter.hash_triple(m2), converter.hash_triple(m1)]
            ),
        )

    def test_keep_references_either(self) -> None:
        """Test keeping references."""
        self.assert_triple_lists([m1, m3], keep_references_either(M123, [r1]))
        self.assert_triple_lists([m1, m2], keep_references_either(M123, [r2]))
        self.assert_triple_lists([m2, m3], keep_references_either(M123, [r3]))
        self.assert_triple_lists(M123, keep_references_either(M123, [r1, r2]))
        self.assert_triple_lists(M123, keep_references_either(M123, [r2, r3]))
        self.assert_triple_lists(M123, keep_references_either(M123, [r1, r2, r3]))

    def test_keep_references_both(self) -> None:
        """Test keeping references."""
        self.assert_triple_lists([m1], keep_references_both(M123, [r1, r2]))
        self.assert_triple_lists([m2], keep_references_both(M123, [r2, r3]))
        self.assert_triple_lists([m3], keep_references_both(M123, [r1, r3]))
        self.assert_triple_lists(M123, keep_references_both(M123, [r1, r2, r3]))

    def test_exclude_references(self) -> None:
        """Test exclude references."""
        self.assert_triple_lists([m2], exclude_references(M123, [r1]))
        self.assert_triple_lists([m3], exclude_references(M123, [r2]))
        self.assert_triple_lists([m1], exclude_references(M123, [r3]))
