"""Test writing I/O."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import curies
from curies import Converter

CHEBI_URI_PREFIX = "http://purl.obolibrary.org/obo/CHEBI_"


class TestIO(unittest.TestCase):
    """Test I/O."""

    def setUp(self) -> None:
        """Set up the test case."""
        self.prefix = "CHEBI"
        self.uri_prefix = CHEBI_URI_PREFIX
        self.prefix_synonym = "p"
        self.uri_prefix_synonym = "u"
        self.converter = Converter.from_extended_prefix_map(
            [
                {
                    "prefix": self.prefix,
                    "prefix_synonyms": [self.prefix_synonym],
                    "uri_prefix": self.uri_prefix,
                    "uri_prefix_synonyms": [self.uri_prefix_synonym],
                },
            ]
        )

    def test_write_epm(self):
        """Test writing and reading an extended prefix map."""
        with TemporaryDirectory() as d:
            path = Path(d).joinpath("test.json")
            curies.write_extended_prefix_map(self.converter, path)
            nc = curies.load_extended_prefix_map(path)
        self.assertEqual(self.converter.records, nc.records)

    def test_write_jsonld_with_bimap(self):
        """Test writing and reading a prefix map via JSON-LD."""
        with TemporaryDirectory() as d:
            path = Path(d).joinpath("test.json")
            curies.write_jsonld_context(self.converter, path.as_posix())
            nc = curies.load_jsonld_context(path)
        self.assertEqual({self.prefix: self.uri_prefix}, nc.prefix_map)
        self.assertEqual(
            {self.uri_prefix: self.prefix},
            nc.reverse_prefix_map,
            msg="the prefix synonym should not survive round trip",
        )
        self.assertEqual({self.prefix: self.uri_prefix}, nc.bimap)

    def test_shacl(self):
        """Test round-tripping SHACL."""
        with TemporaryDirectory() as d:
            path = Path(d).joinpath("test.ttl")
            curies.write_shacl(self.converter, path)
            nc = curies.load_shacl(path)
        self.assertEqual(self.converter.bimap, nc.bimap)
