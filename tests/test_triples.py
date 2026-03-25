"""Tests for triples."""

import itertools as itt
import tempfile
import unittest
from pathlib import Path

import pydantic

import curies
from curies import Reference, Triple
from curies.triples import encode_delimited_uris, read_triples, write_triples

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

    def test_hash_uri_triple(self) -> None:
        """Test URL-safe base64 encoding and decoding of triples."""
        examples: list[tuple[str, str, str, str]] = [
            (  # example 1 from https://ts4nfdi.github.io/mapping-sameness-identifier/
                "95a088082ab2b2a68638aebbcc3fe3e0f229da75a8b5bdbb9f3f8cd5e1e4286e",
                "http://example.org/feline",
                "http://www.w3.org/2002/07/owl#sameAs",
                "http://example.com/cat",
            ),
            (
                "36a1f9244ea7641a90987c82f33c25c0c13712ee8f48207b2a0825f8a4e4e26a",
                "http://id.nlm.nih.gov/mesh/C000089",
                "http://www.w3.org/2004/02/skos/core#exactMatch",
                "http://purl.obolibrary.org/obo/CHEBI_28646",
            ),
        ]
        for expected, s, p, o in examples:
            with self.subTest():
                self.assertEqual(expected, encode_delimited_uris((s, p, o)))

    def test_hash_triple(self) -> None:
        """Test URL-safe base64 encoding and decoding of triples."""
        converter = curies.load_prefix_map(
            {
                "mesh": "http://id.nlm.nih.gov/mesh/",
                "skos": "http://www.w3.org/2004/02/skos/core#",
                "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
            }
        )
        triple = Triple(subject="mesh:C000089", predicate="skos:exactMatch", object="CHEBI:28646")
        triple_id = converter.hash_triple(triple)

        self.assertEqual(
            "36a1f9244ea7641a90987c82f33c25c0c13712ee8f48207b2a0825f8a4e4e26a",
            triple_id,
        )
