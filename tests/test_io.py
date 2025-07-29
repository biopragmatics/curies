"""Test writing I/O."""

import json
import unittest
from collections.abc import Iterable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

import rdflib

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
        self.pattern = "^\\d{7}$"
        self.converter = Converter.from_extended_prefix_map(
            [
                {
                    "prefix": self.prefix,
                    "prefix_synonyms": [self.prefix_synonym],
                    "uri_prefix": self.uri_prefix,
                    "uri_prefix_synonyms": [self.uri_prefix_synonym],
                    "pattern": self.pattern,
                },
            ]
        )

    def test_write_epm(self) -> None:
        """Test writing and reading an extended prefix map."""
        with TemporaryDirectory() as d:
            path = Path(d).joinpath("test.json")
            curies.write_extended_prefix_map(self.converter, path)
            nc = curies.load_extended_prefix_map(path)
        self.assertEqual(self.converter.records, nc.records)
        self.assertEqual({self.prefix: self.pattern}, nc.pattern_map)

    def test_write_jsonld_with_bimap(self) -> None:
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

    def test_write_jsonld_with_synonyms(self) -> None:
        """Test writing a JSON-LD with synonyms."""
        # note: we don't test loading since loading a JSON-LD with synonyms is undefined
        for expand in [True, False]:
            with self.subTest(expand=expand):
                with TemporaryDirectory() as d:
                    path = Path(d).joinpath("test.json")
                    curies.write_jsonld_context(self.converter, path, include_synonyms=True)
                    data = json.loads(path.read_text())["@context"]
                self.assertEqual({self.prefix, self.prefix_synonym}, set(data))

    def test_shacl(self) -> None:
        """Test round-tripping SHACL."""
        with TemporaryDirectory() as d:
            path = Path(d).joinpath("test.ttl")
            curies.write_shacl(self.converter, path)
            nc = curies.load_shacl(path)
        self.assertEqual(self.converter.bimap, nc.bimap)
        self.assertEqual({self.prefix: self.pattern}, nc.pattern_map)

    def test_shacl_with_synonyms(self) -> None:
        """Test writing SHACL with synonyms."""
        # note: we don't test loading since loading SHACL with synonyms is undefined
        with TemporaryDirectory() as d:
            path = Path(d).joinpath("test.ttl")
            curies.write_shacl(self.converter, path, include_synonyms=True)
            graph = rdflib.Graph()
            graph.parse(location=path.as_posix(), format="turtle")

        query = """\
            SELECT ?prefix
            WHERE {
                ?bnode sh:declare ?declaration .
                ?declaration sh:prefix ?prefix .
            }
        """
        results = cast(Iterable[tuple[str]], graph.query(query))
        self.assertEqual({self.prefix, self.prefix_synonym}, {str(prefix) for (prefix,) in results})
