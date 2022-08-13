# -*- coding: utf-8 -*-

"""Trivial version test."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

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
        self.assertEqual({"CHEBI", "MONDO", "GO", "OBO"}, self.converter.get_prefixes())

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
        self.assertIn("rdf", semweb_converter.prefix_map)

        bioregistry_converter = get_bioregistry_converter()
        self.assertIn("chebi", bioregistry_converter.prefix_map)
        self.assertNotIn("CHEBI", bioregistry_converter.prefix_map)

        obo_converter = get_obo_converter()
        self.assertIn("CHEBI", obo_converter.prefix_map)
        self.assertNotIn("chebi", obo_converter.prefix_map)

        monarch_converter = get_monarch_converter()
        self.assertIn("CHEBI", monarch_converter.prefix_map)
        self.assertNotIn("chebi", monarch_converter.prefix_map)

        go_converter = get_go_converter()
        self.assertIn("CHEBI", go_converter.prefix_map)
        self.assertNotIn("chebi", go_converter.prefix_map)

        go_obo_converter = get_go_obo_converter()
        self.assertIn("CHEBI", go_obo_converter.prefix_map)
        self.assertNotIn("chebi", go_obo_converter.prefix_map)

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
        self.assertNotIn("nope", converter.prefix_map)

    def test_df_bulk(self):
        """Test bulk processing in pandas dataframes."""
        rows = [
            ("CHEBI:1", "http://purl.obolibrary.org/obo/CHEBI_1"),
        ]
        df = pd.DataFrame(rows, columns=["curie", "uri"])
        self.converter.pd_expand(df, "curie")
        self.assertTrue((df.curie == df.uri).all())

        df = pd.DataFrame(rows, columns=["curie", "uri"])
        self.converter.pd_compress(df, "uri")
        self.assertTrue((df.curie == df.uri).all())

    def test_file_bulk(self):
        """Test bulk processing of files."""
        with TemporaryDirectory() as directory:
            for rows, header in [
                (
                    [
                        ("curie", "uri"),
                        ("CHEBI:1", "http://purl.obolibrary.org/obo/CHEBI_1"),
                    ],
                    True,
                ),
                (
                    [
                        ("CHEBI:1", "http://purl.obolibrary.org/obo/CHEBI_1"),
                    ],
                    False,
                ),
            ]:
                path = Path(directory).joinpath("test.tsv")
                with path.open("w") as file:
                    for row in rows:
                        print(*row, sep="\t", file=file)  # noqa:T201

                idx = 1 if header else 0

                self.converter.file_expand(path, 0, header=header)
                lines = [line.strip().split("\t") for line in path.read_text().splitlines()]
                self.assertEqual("http://purl.obolibrary.org/obo/CHEBI_1", lines[idx][0])

                self.converter.file_compress(path, 0, header=header)
                lines = [line.strip().split("\t") for line in path.read_text().splitlines()]
                self.assertEqual("CHEBI:1", lines[idx][0])


class TestVersion(unittest.TestCase):
    """Trivially test a version."""

    def test_version_type(self):
        """Test the version is a string.

        This is only meant to be an example test.
        """
        version = get_version()
        self.assertIsInstance(version, str)
