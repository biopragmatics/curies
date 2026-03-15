"""Test URL-safe base64 encoding and decoding of triples."""

import unittest

from curies import Converter, Triple
from curies.hash_triple import decode_triple, encode_triple


class TestHashTriple(unittest.TestCase):
    """Test URL-safe base64 encoding and decoding of triples."""

    def test_hash_triple(self) -> None:
        """Test URL-safe base64 encoding and decoding of triples."""
        converter = Converter()
        converter.add_prefix("a", "https://example.org/a:")
        converter.add_prefix("b", "https://example.org/b:")
        converter.add_prefix("c", "https://example.org/c:")
        a = converter.parse_curie("a:1", strict=True).to_pydantic()
        b = converter.parse_curie("b:1", strict=True).to_pydantic()
        c = converter.parse_curie("c:1", strict=True).to_pydantic()
        t = Triple(subject=a, predicate=b, object=c)

        s = encode_triple(converter, t)

        self.assertEqual(
            "aHR0cHM6Ly9leGFtcGxlLm9yZy9hOjEJaHR0cHM6Ly9leGFtcGxlLm9yZy9iOjEJaHR0cHM6Ly9leGFtcGxlLm9yZy9jOjE=",
            s,
        )

        t2 = decode_triple(converter, s)
        self.assertEqual(t, t2)
