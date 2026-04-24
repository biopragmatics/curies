"""Test triples operations."""

import unittest

from curies.triples import Triple
from curies.triples.ops import get_many_to_many, get_subject_object_indexes

predicate = "skos:exactMatch"  # could be anything, this gests ignored by this operation
# one-to-one
m1 = Triple.from_curies("p1:1", predicate, "p2:A")
# one-to-many
m2 = Triple.from_curies("p1:2", predicate, "p2:B")
m3 = Triple.from_curies("p1:2", predicate, "p2:C")
# many-to-one
m4 = Triple.from_curies("p1:4", predicate, "p2:D")
m5 = Triple.from_curies("p1:5", predicate, "p2:D")
# many-to-many
m6 = Triple.from_curies("p1:6", predicate, "p2:E")
m7 = Triple.from_curies("p1:6", predicate, "p2:F")
m8 = Triple.from_curies("p1:7", predicate, "p2:E")
m9 = Triple.from_curies("p1:7", predicate, "p2:F")

m10 = Triple.from_curies("p1:1", predicate, "p3:gamma")

# duplicate of m1
m11 = Triple.from_curies("p1:1", predicate, "p2:A")

triples = [m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11]


class TestOperations(unittest.TestCase):
    """Test triples operations."""

    def get_many_to_many(self) -> None:
        """Test getting many-to-many triples."""
        self.assertEqual([m6, m7, m8, m9], get_many_to_many(triples))

    def test_many_to_many_index(self) -> None:
        """Get getting a many-to-many index."""
        forward, _backward = get_subject_object_indexes(triples)
        self.assertEqual(
            {
                ("p1", "p2"): {
                    "1": {"A": [m1, m11]},
                    "2": {"B": [m2], "C": [m3]},
                    "4": {"D": [m4]},
                    "5": {"D": [m5]},
                    "6": {"E": [m6], "F": [m7]},
                    "7": {"E": [m8], "F": [m9]},
                },
                ("p1", "p3"): {"1": {"gamma": [m10]}},
            },
            forward,
        )
