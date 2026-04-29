"""Test triples operations."""

import unittest

from curies import Reference
from curies.triples import Triple
from curies.triples.ops import (
    flip_prefix_pair_stratified_index,
    get_one_to_many,
    get_prefix_pair_stratified_indexes,
    get_prefix_stratified_many_to_many,
    get_reference_indexes,
)
from curies.vocabulary import exact_match

predicate = exact_match

p11 = Reference.from_curie("p1:1")
p12 = Reference.from_curie("p1:2")
p13 = Reference.from_curie("p1:3")
p14 = Reference.from_curie("p1:4")
p15 = Reference.from_curie("p1:5")
p16 = Reference.from_curie("p1:6")
p17 = Reference.from_curie("p1:7")

p2a = Reference.from_curie("p2:A")
p2b = Reference.from_curie("p2:B")
p2c = Reference.from_curie("p2:C")
p2d = Reference.from_curie("p2:D")
p2e = Reference.from_curie("p2:E")
p2f = Reference.from_curie("p2:F")

p3gamma = Reference.from_curie("p3:gamma")


def _triple(a: Reference, b: Reference, c: Reference) -> Triple:
    return Triple(subject=a, predicate=b, object=c)


# one-to-one
m1 = _triple(p11, predicate, p2a)
# one-to-many
m2 = _triple(p12, predicate, p2b)
m3 = _triple(p12, predicate, p2c)
# many-to-one
m4 = _triple(p14, predicate, p2d)
m5 = _triple(p15, predicate, p2d)
# many-to-many
m6 = _triple(p16, predicate, p2e)
m7 = _triple(p16, predicate, p2f)
m8 = _triple(p17, predicate, p2e)
m9 = _triple(p17, predicate, p2f)

m10 = _triple(p11, predicate, p3gamma)

# duplicate of m1
m11 = _triple(p11, predicate, p2a)

triples = [m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11]


class TestOperations(unittest.TestCase):
    """Test triples operations."""

    def test_many_to_many_index(self) -> None:
        """Get getting a many-to-many index."""
        self.maxDiff = None
        forward, backward = get_prefix_pair_stratified_indexes(triples)
        with self.subTest(part="contents"):
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
            self.assertEqual(
                {
                    ("p2", "p1"): {
                        "A": {"1": [m1, m11]},
                        "B": {"2": [m2]},
                        "C": {"2": [m3]},
                        "D": {"4": [m4], "5": [m5]},
                        "E": {"6": [m6], "7": [m8]},
                        "F": {"6": [m7], "7": [m9]},
                    },
                    ("p3", "p1"): {
                        "gamma": {"1": [m10]},
                    },
                },
                backward,
            )

        with self.subTest(part="processing"):
            self.assertEqual(
                {
                    ("p1", "p2"): {
                        "2": {"B": [m2], "C": [m3]},
                        "6": {"E": [m6], "F": [m7]},
                        "7": {"E": [m8], "F": [m9]},
                    },
                },
                get_one_to_many(forward),
                msg="\nfailed on 1-n (forward)",
            )
            self.assertEqual(
                {
                    ("p2", "p1"): {
                        "D": {"4": [m4], "5": [m5]},
                        "E": {"6": [m6], "7": [m8]},
                        "F": {"6": [m7], "7": [m9]},
                    }
                },
                get_one_to_many(backward),
                msg="\nfailed on n-1 (backward)",
            )
            self.assertEqual(
                {
                    ("p1", "p2"): {
                        "6": {"E": [m6], "F": [m7]},
                        "7": {"E": [m8], "F": [m9]},
                    },
                },
                flip_prefix_pair_stratified_index(get_one_to_many(backward)),
                msg="\nfailed on n-1 (backward, flipped)",
            )

    def test_simple_indexes(self) -> None:
        """Test getting many-to-many triples."""
        forward, backward = get_reference_indexes(triples)
        self.assertEqual(
            {
                p11: {p2a, p3gamma},
                p12: {p2b, p2c},
                p14: {p2d},
                p15: {p2d},
                p16: {p2e, p2f},
                p17: {p2e, p2f},
            },
            forward,
        )
        self.assertEqual(
            {
                p2a: {p11},
                p2b: {p12},
                p2c: {p12},
                p2d: {p14, p15},
                p2e: {p16, p17},
                p2f: {p16, p17},
                p3gamma: {p11},
            },
            backward,
        )

    def test_get_many_to_many(self) -> None:
        """Test getting many-to-many triples."""
        self.assertEqual({m6, m7, m8, m9}, get_prefix_stratified_many_to_many(triples))
