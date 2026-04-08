"""Test filter functions."""

import unittest

from curies import Triple
from curies.triples import (
    exclude_object_prefixes,
    exclude_prefixes,
    exclude_same_prefixes,
    exclude_subject_prefixes,
    keep_object_prefixes,
    keep_prefixes,
    keep_subject_prefixes,
)
from curies.vocabulary import exact_match, subclass_of

c1, c2, c3, c4 = "DOID:0050577", "mesh:C562966", "umls:C4551571", "DOID:225"
m1 = Triple.from_curies(c1, exact_match.curie, c2)
m2 = Triple.from_curies(c2, exact_match.curie, c3)
m3 = Triple.from_curies(c1, exact_match.curie, c3)
m4 = Triple.from_curies(c1, subclass_of.curie, c4)


class TestFilters(unittest.TestCase):
    """Test filters."""

    def exclude_object_prefixes(self) -> None:
        """Test excluding object prefixes."""
        self.assertEqual(
            [m1],
            list(exclude_object_prefixes([m1, m2, m3], {"umls"})),
        )
        self.assertEqual([m2, m3], list(exclude_object_prefixes([m1, m2, m3], {"mesh"})))
        self.assertEqual([m1, m2, m3], list(exclude_object_prefixes([m1, m2, m3], {"DOID"})))

    def exclude_prefixes(self) -> None:
        """Test excluding prefixes."""
        self.assertEqual([m1], list(exclude_prefixes([m1, m2, m3], {"umls"})))
        self.assertEqual([m2], list(exclude_prefixes([m1, m2, m3], {"DOID"})))
        self.assertEqual([m3], list(exclude_prefixes([m1, m2, m3], {"mesh"})))

    def exclude_subject_prefixes(self) -> None:
        """Test excluding subject prefixes."""
        self.assertEqual([m2], list(exclude_subject_prefixes([m1, m2, m3], {"DOID"})))
        self.assertEqual([m1, m2, m3], list(exclude_subject_prefixes([m1, m2, m3], {"umls"})))
        self.assertEqual([m1, m3], list(exclude_subject_prefixes([m1, m2, m3], {"mesh"})))

    def exclude_same_prefixes(self) -> None:
        """Test excluding same prefixes."""
        self.assertEqual([m1, m2, m3], list(exclude_same_prefixes([m1, m2, m3, m4])))

    def keep_object_prefixes(self) -> None:
        """Test keeping object prefixes."""
        self.assertEqual([m2, m3], list(keep_object_prefixes([m1, m2, m3], {"umls"})))

    def keep_prefixes(self) -> None:
        """Test keeping prefixes."""
        self.assertEqual([m1], list(keep_prefixes([m1, m2, m3], {"DOID", "mesh"})))

    def keep_subject_prefixes(self) -> None:
        """Test keeping subject prefixes."""
        self.assertEqual([m1, m2], list(keep_subject_prefixes([m1, m2, m3], {"DOID"})))
