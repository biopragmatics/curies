"""Tests for triples."""

import itertools as itt
import tempfile
import unittest
from pathlib import Path

import pydantic

from curies import Converter, Reference, Triple
from curies.triples import decode_triple, encode_triple, read_triples, write_triples

T1 = Triple.from_curies("a:1", "a:2", "a:3")
T2 = Triple.from_curies("a:1", "a:2", "a:4")


class TestTriples(unittest.TestCase):
    """Test triples."""

    def test_immutable(self) -> None:
        """Test immutable."""
        with self.assertRaises(pydantic.ValidationError):
            T1.subject = Reference.from_curie("b:1")  # type:ignore

    def test_as_curies(self) -> None:
        """Test stringifying."""
        self.assertEqual(
            ("a:1", "a:2", "a:3"),
            T1.as_str_triple(),
        )

    def test_roundtrip(self) -> None:
        """Test roundtrip."""
        triples = [T1, T2]
        with tempfile.TemporaryDirectory() as directory:
            paths = [
                Path(directory).joinpath("test.tsv.gz"),
                Path(directory).joinpath("test.tsv"),
            ]
            headers = [None, ("a", "b", "c")]
            for path, header in itt.product(paths, headers):
                with self.subTest(path=path):
                    write_triples(triples, path, header=header)
                    reconstituted = read_triples(path)
                    self.assertEqual(triples, reconstituted)

    def test_sort(self) -> None:
        """Test sorting."""
        self.assertEqual([T1, T2], sorted([T1, T2]))
        self.assertEqual([T1, T2], sorted([T2, T1]))

    def test_hash_triple(self) -> None:
        """Test URL-safe base64 encoding and decoding of triples."""
        converter = Converter()
        converter.add_prefix("a", "https://example.org/a:")
        converter.add_prefix("b", "https://example.org/b:")
        converter.add_prefix("c", "https://example.org/c:")
        subject = converter.parse_curie("a:1", strict=True).to_pydantic()
        predicate = converter.parse_curie("b:1", strict=True).to_pydantic()
        obj = converter.parse_curie("c:1", strict=True).to_pydantic()

        triple = Triple(subject=subject, predicate=predicate, object=obj)
        triple_id = encode_triple(converter, triple)

        self.assertEqual(
            "aHR0cHM6Ly9leGFtcGxlLm9yZy9hOjEJaHR0cHM6Ly9leGFtcGxlLm9yZy9iOjEJaHR0cHM6Ly9leGFtcGxlLm9yZy9jOjE=",
            triple_id,
        )

        t2 = decode_triple(converter, triple_id)
        self.assertEqual(triple, t2)
