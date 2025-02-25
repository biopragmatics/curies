"""Tests for triples."""

import tempfile
import unittest
from pathlib import Path

from curies import Triple
from curies.triples import read_triples, write_triples


class TestTriples(unittest.TestCase):
    """Test triples."""

    def test_roundtrip(self) -> None:
        """Test roundtrip."""
        triples = [
            Triple.from_curies("a:1", "a:2", "a:3"),
            Triple.from_curies("a:1", "a:2", "a:4"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for path in [
                Path(directory).joinpath("test.tsv.gz"),
                Path(directory).joinpath("test.tsv"),
            ]:
                with self.subTest(path=path):
                    write_triples(triples, path)
                    reconstituted = read_triples(path)
                    self.assertEqual(triples, reconstituted)
