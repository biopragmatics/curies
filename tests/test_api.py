# -*- coding: utf-8 -*-

"""Trivial version test."""

import unittest

from curies.api import Converter
from curies.version import get_version


class TestConverter(unittest.TestCase):
    """Test the converter class."""

    def setUp(self) -> None:
        """Set up the converter test case."""
        self.converter = Converter.from_prefix_map(
            {
                "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
                "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
                "GO": "http://purl.obolibrary.org/obo/GO_",
                "OBO": "http://purl.obolibrary.org/obo/",
            }
        )

    def test_convert(self):
        """Test compression."""
        for curie, uri in [
            ("CHEBI:1", "http://purl.obolibrary.org/obo/CHEBI_1"),
            ("OBO:unnamespaced", "http://purl.obolibrary.org/obo/unnamespaced"),
        ]:
            self.assertEqual(curie, self.converter.compress(uri))
            self.assertEqual(uri, self.converter.expand(curie))

        self.assertIsNone(self.converter.compress("http://example.org/missing:00000"))
        self.assertIsNone(self.converter.expand("missing:00000"))

    def test_remote(self):
        """Test loading a remote JSON-LD context."""
        with self.assertRaises(ValueError):
            # missing end .jsonld file
            Converter.from_jsonld_github("biopragmatics", "bioregistry")

        converter = Converter.from_jsonld_github(
            "biopragmatics", "bioregistry", "exports", "contexts", "semweb.context.jsonld"
        )
        self.assertIn("rdf", converter.data)


class TestVersion(unittest.TestCase):
    """Trivially test a version."""

    def test_version_type(self):
        """Test the version is a string.

        This is only meant to be an example test.
        """
        version = get_version()
        self.assertIsInstance(version, str)
