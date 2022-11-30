# -*- coding: utf-8 -*-

"""Trivial version test."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from bioregistry.export.prefix_maps import EXTENDED_PREFIX_MAP_PATH

from curies.api import Converter, DuplicatePrefixes, DuplicateURIPrefixes, Record, chain
from curies.sources import (
    BIOREGISTRY_CONTEXTS,
    get_bioregistry_converter,
    get_go_converter,
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

    def test_invalid_record(self):
        """Test throwing an error for invalid records."""
        with self.assertRaises(ValueError):
            Record(
                prefix="chebi",
                uri_prefix="http://purl.obolibrary.org/obo/CHEBI_",
                prefix_synonyms=["chebi"],
            )
        with self.assertRaises(ValueError):
            Record(
                prefix="chebi",
                uri_prefix="http://purl.obolibrary.org/obo/CHEBI_",
                uri_prefix_synonyms=["http://purl.obolibrary.org/obo/CHEBI_"],
            )

    def test_invalid_records(self):
        """Test throwing an error for duplicated URI prefixes."""
        with self.assertRaises(DuplicateURIPrefixes) as e:
            Converter.from_prefix_map(
                {
                    "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
                    "nope": "http://purl.obolibrary.org/obo/CHEBI_",
                }
            )
        self.assertIsInstance(str(e.exception), str)
        with self.assertRaises(DuplicatePrefixes) as e:
            Converter(
                [
                    Record(prefix="chebi", uri_prefix="https://bioregistry.io/chebi:"),
                    Record(prefix="chebi", uri_prefix="http://purl.obolibrary.org/obo/CHEBI_"),
                ],
            )
        self.assertIsInstance(str(e.exception), str)

        # No failure
        Converter.from_prefix_map(
            {
                "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
                "nope": "http://purl.obolibrary.org/obo/CHEBI_",
            },
            strict=False,
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

        for web in [True, False]:
            bioregistry_converter = get_bioregistry_converter(web=web)
            self.assert_bioregistry_converter(bioregistry_converter)

        c = Converter.from_reverse_prefix_map_url(f"{BIOREGISTRY_CONTEXTS}/bioregistry.rpm.json")
        self.assertIn("chebi", c.prefix_map)
        self.assertNotIn("CHEBI", c.prefix_map)

        obo_converter = get_obo_converter()
        self.assertIn("CHEBI", obo_converter.prefix_map)
        self.assertNotIn("chebi", obo_converter.prefix_map)

        monarch_converter = get_monarch_converter()
        self.assertIn("CHEBI", monarch_converter.prefix_map)
        self.assertNotIn("chebi", monarch_converter.prefix_map)

        go_converter = get_go_converter()
        self.assertIn("CHEBI", go_converter.prefix_map)
        self.assertNotIn("chebi", go_converter.prefix_map)

    def assert_bioregistry_converter(self, converter: Converter) -> None:
        """Assert the bioregistry converter has the right stuff in it."""
        records = {records.prefix: records for records in converter.records}
        self.assertIn("chebi", records)
        record = records["chebi"]
        self.assertIsInstance(record, Record)
        self.assertEqual("chebi", record.prefix)
        self.assertIn("CHEBI", record.prefix_synonyms)
        self.assertIn("ChEBI", record.prefix_synonyms)

        self.assertIn("chebi", converter.prefix_map)
        # Synonyms that are non-conflicting also get added
        self.assertIn("CHEBI", converter.prefix_map)
        chebi_uri = converter.prefix_map["chebi"]
        self.assertIn(chebi_uri, converter.reverse_prefix_map)
        self.assertEqual("chebi", converter.reverse_prefix_map[chebi_uri])

    @unittest.skipUnless(
        EXTENDED_PREFIX_MAP_PATH.is_file(),
        reason="missing local, editable installation of the Bioregistry",
    )
    def test_bioregistry_editable(self):
        """Test loading the bioregistry extended prefix map locally."""
        records = json.loads(EXTENDED_PREFIX_MAP_PATH.read_text())
        converter = Converter.from_extended_prefix_map(records)
        self.assert_bioregistry_converter(converter)

    def test_reverse_constructor(self):
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

        c1 = Converter.from_priority_prefix_map(
            {
                "CHEBI": ["http://purl.obolibrary.org/obo/CHEBI_", "https://bioregistry.io/chebi:"],
                "MONDO": ["http://purl.obolibrary.org/obo/MONDO_"],
            }
        )
        c2 = Converter.from_priority_prefix_map(
            {
                "CHEBI": [
                    "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=",
                    "http://identifiers.org/chebi/",
                    "http://purl.obolibrary.org/obo/CHEBI_",
                ],
                "GO": ["http://purl.obolibrary.org/obo/GO_"],
                "OBO": ["http://purl.obolibrary.org/obo/"],
            }
        )
        converter = chain([c1, c2], case_sensitive=True)
        for url in [
            "http://purl.obolibrary.org/obo/CHEBI_138488",
            "https://bioregistry.io/chebi:138488",
            "http://identifiers.org/chebi/138488",
            "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=138488",
        ]:
            self.assertEqual("CHEBI:138488", converter.compress(url))
        self.assertEqual(
            "GO:0000001",
            converter.compress("http://purl.obolibrary.org/obo/GO_0000001"),
        )
        self.assertEqual(
            "http://purl.obolibrary.org/obo/CHEBI_138488",
            converter.expand("CHEBI:138488"),
        )
        self.assertNotIn("nope", converter.get_prefixes())

    def test_combine_ci(self):
        """Test combining case insensitive."""
        c1 = Converter.from_priority_prefix_map(
            {
                "CHEBI": [
                    "http://purl.obolibrary.org/obo/CHEBI_",
                    "https://bioregistry.io/chebi:",
                ],
            }
        )
        c2 = Converter.from_reverse_prefix_map(
            {
                "http://identifiers.org/chebi/": "chebi",
                "http://identifiers.org/chebi:": "chebi",
            }
        )
        converter = chain([c1, c2], case_sensitive=False)
        self.assertEqual({"CHEBI"}, converter.get_prefixes())
        for url in [
            "http://purl.obolibrary.org/obo/CHEBI_138488",
            "http://identifiers.org/chebi/138488",
            "http://identifiers.org/chebi:138488",
            "https://bioregistry.io/chebi:138488",
        ]:
            self.assertEqual("CHEBI:138488", converter.compress(url))
        # use the first prefix map for expansions
        self.assertEqual(
            "http://purl.obolibrary.org/obo/CHEBI_138488",
            converter.expand("CHEBI:138488"),
        )

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
