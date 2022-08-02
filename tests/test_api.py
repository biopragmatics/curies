# -*- coding: utf-8 -*-

"""Trivial version test."""

import unittest

from curies.api import Converter, chain
from curies.sources import (
    get_bioregistry_converter,
    get_go_converter,
    get_go_obo_converter,
    get_monarch_converter,
    get_obo_converter,
)
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

        semweb_converter = Converter.from_jsonld_github(
            "biopragmatics", "bioregistry", "exports", "contexts", "semweb.context.jsonld"
        )
        self.assertIn("rdf", semweb_converter.data)

        bioregistry_converter = get_bioregistry_converter()
        self.assertIn("chebi", bioregistry_converter.data)
        self.assertNotIn("CHEBI", bioregistry_converter.data)

        obo_converter = get_obo_converter()
        self.assertIn("CHEBI", obo_converter.data)
        self.assertNotIn("chebi", obo_converter.data)

        monarch_converter = get_monarch_converter()
        self.assertIn("CHEBI", monarch_converter.data)
        self.assertNotIn("chebi", monarch_converter.data)

        go_converter = get_go_converter()
        self.assertIn("CHEBI", go_converter.data)
        self.assertNotIn("chebi", go_converter.data)

        go_obo_converter = get_go_obo_converter()
        self.assertIn("CHEBI", go_obo_converter.data)
        self.assertNotIn("chebi", go_obo_converter.data)

    def test_reverse_constuctor(self):
        """Test constructing from a reverse prefix map."""
        converter = Converter.from_reverse_prefix_map(
            {
                "http://purl.obolibrary.org/obo/CHEBI_": "CHEBI",
                "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=": "CHEBI",
                "http://purl.obolibrary.org/obo/MONDO_": "MONDO",
            }
        )
        self.assertEqual(
            "http://purl.obolibrary.org/obo/CHEBI_138488", converter.expand("CHEBI:138488")
        )

        self.assertEqual(
            "CHEBI:138488", converter.compress("http://purl.obolibrary.org/obo/CHEBI_138488")
        )
        self.assertEqual(
            "CHEBI:138488",
            converter.compress("https://www.ebi.ac.uk/chebi/searchId.do?chebiId=138488"),
        )

    def test_combine(self):
        """Test chaining converters."""
        with self.assertRaises(ValueError):
            chain([])

        c1 = Converter.from_prefix_map(
            {
                "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
                "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
            }
        )
        c2 = Converter.from_prefix_map(
            {
                "CHEBI": "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=",
                "GO": "http://purl.obolibrary.org/obo/GO_",
                "OBO": "http://purl.obolibrary.org/obo/",
                # This will get overridden
                "nope": "http://purl.obolibrary.org/obo/CHEBI_",
            }
        )
        converter = chain([c1, c2])
        self.assertEqual(
            "CHEBI:138488",
            converter.compress("http://purl.obolibrary.org/obo/CHEBI_138488"),
        )
        self.assertEqual(
            "CHEBI:138488",
            converter.compress("https://www.ebi.ac.uk/chebi/searchId.do?chebiId=138488"),
        )
        self.assertEqual(
            "GO:0000001",
            converter.compress("http://purl.obolibrary.org/obo/GO_0000001"),
        )
        self.assertNotIn("nope", converter.data)


class TestVersion(unittest.TestCase):
    """Trivially test a version."""

    def test_version_type(self):
        """Test the version is a string.

        This is only meant to be an example test.
        """
        version = get_version()
        self.assertIsInstance(version, str)
