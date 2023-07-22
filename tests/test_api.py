# -*- coding: utf-8 -*-

"""Trivial version test."""

import json
import tempfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import rdflib
from bioregistry.export.prefix_maps import EXTENDED_PREFIX_MAP_PATH

from curies.api import (
    CompressionError,
    Converter,
    DuplicatePrefixes,
    DuplicateURIPrefixes,
    ExpansionError,
    Record,
    Reference,
    ReferenceTuple,
    chain,
)
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
        self.simple_obo_prefix_map = {
            "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
            "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
            "GO": "http://purl.obolibrary.org/obo/GO_",
            "OBO": "http://purl.obolibrary.org/obo/",
        }
        self.converter = Converter.from_prefix_map(self.simple_obo_prefix_map)

    def test_reference_tuple(self):
        """Test the reference tuple data type."""
        t = ReferenceTuple("chebi", "1234")
        self.assertEqual("chebi:1234", t.curie)
        self.assertEqual(t, ReferenceTuple.from_curie("chebi:1234"))

    def test_reference_pydantic(self):
        """Test the reference Pydantic model."""
        t = Reference(prefix="chebi", identifier="1234")
        self.assertEqual("chebi:1234", t.curie)
        self.assertEqual(t, Reference.from_curie("chebi:1234"))

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
        self._assert_convert(self.converter)

    def _assert_convert(self, converter: Converter):
        self.assertIn("GO", converter.prefix_map)
        self.assertIn("http://purl.obolibrary.org/obo/GO_", converter.reverse_prefix_map)
        self.assertIn("http://purl.obolibrary.org/obo/GO_", converter.trie)
        for curie, uri in [
            ("CHEBI:1", "http://purl.obolibrary.org/obo/CHEBI_1"),
            ("OBO:unnamespaced", "http://purl.obolibrary.org/obo/unnamespaced"),
        ]:
            self.assertEqual(curie, converter.compress(uri))
            self.assertEqual(curie, converter.compress_strict(uri))
            self.assertEqual(uri, converter.expand(curie))
            self.assertEqual(uri, converter.expand_strict(curie))

        self.assertIsNone(converter.compress("http://example.org/missing:00000"))
        with self.assertRaises(CompressionError):
            converter.compress_strict("http://example.org/missing:00000")

        self.assertIsNone(converter.expand("missing:00000"))
        with self.assertRaises(ExpansionError):
            converter.expand_strict("missing:00000")

        self.assertLess(0, len(converter.records), msg="converter has no records")
        self.assertIsNone(converter.get_record("nope"))
        self.assertIsNone(converter.get_record("go"), msg="synonym lookup is not allowed here")
        record = converter.get_record("GO")
        self.assertIsNotNone(record, msg=f"records: {[r.prefix for r in converter.records]}")
        self.assertIsInstance(record, Record)
        self.assertEqual("GO", record.prefix)

    def test_bioregistry(self):
        """Test loading a remote JSON-LD context."""
        for web in [True, False]:
            bioregistry_converter = get_bioregistry_converter(web=web)
            self.assert_bioregistry_converter(bioregistry_converter)

        c = Converter.from_reverse_prefix_map(f"{BIOREGISTRY_CONTEXTS}/bioregistry.rpm.json")
        self.assertIn("chebi", c.prefix_map)
        self.assertNotIn("CHEBI", c.prefix_map)

    def test_from_github(self):
        """Test getting a JSON-LD map from GitHub."""
        with self.assertRaises(ValueError):
            # missing end .jsonld file
            Converter.from_jsonld_github("biopragmatics", "bioregistry")

        semweb_converter = Converter.from_jsonld_github(
            "biopragmatics", "bioregistry", "exports", "contexts", "semweb.context.jsonld"
        )
        self.assertIn("rdf", semweb_converter.prefix_map)

    def test_obo(self):
        """Test the OBO converter."""
        obo_converter = get_obo_converter()
        self.assertIn("CHEBI", obo_converter.prefix_map)
        self.assertNotIn("chebi", obo_converter.prefix_map)

    def test_monarch(self):
        """Test the Monarch converter."""
        monarch_converter = get_monarch_converter()
        self.assertIn("CHEBI", monarch_converter.prefix_map)
        self.assertNotIn("chebi", monarch_converter.prefix_map)

    def test_go_registry(self):
        """Test the GO registry converter."""
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

    def test_load_path(self):
        """Test loading from paths."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).joinpath("pm.json")
            with self.assertRaises(FileNotFoundError):
                Converter.from_prefix_map(path)
            with self.assertRaises(FileNotFoundError):
                Converter.from_prefix_map(str(path))

            path.write_text(json.dumps(self.converter.prefix_map))

            c1 = Converter.from_prefix_map(path)
            self.assertEqual(self.converter.prefix_map, c1.prefix_map)

            c2 = Converter.from_prefix_map(str(path))
            self.assertEqual(self.converter.prefix_map, c2.prefix_map)

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

    def test_standardize_curie(self):
        """Test standardize CURIE."""
        converter = Converter.from_extended_prefix_map(
            [
                Record(
                    prefix="CHEBI",
                    prefix_synonyms=["chebi"],
                    uri_prefix="http://purl.obolibrary.org/obo/CHEBI_",
                    uri_prefix_synonyms=[
                        "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:",
                    ],
                ),
            ]
        )
        self.assertEqual("CHEBI:138488", converter.standardize_curie("chebi:138488"))
        self.assertEqual("CHEBI:138488", converter.standardize_curie("CHEBI:138488"))
        self.assertIsNone(converter.standardize_curie("NOPE:NOPE"))

        self.assertEqual(
            "http://purl.obolibrary.org/obo/CHEBI_138488",
            converter.standardize_uri(
                "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:138488"
            ),
        )
        self.assertEqual(
            "http://purl.obolibrary.org/obo/CHEBI_138488",
            converter.standardize_uri("http://purl.obolibrary.org/obo/CHEBI_138488"),
        )
        self.assertIsNone(converter.standardize_uri("NOPE"))

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

    def test_df_standardize(self):
        """Test standardizing dataframes."""
        converter = Converter([])
        converter.add_prefix(
            "chebi",
            "http://purl.obolibrary.org/obo/CHEBI_",
            prefix_synonyms=["CHEBI"],
            uri_prefix_synonyms=["https://bioregistry.io/chebi:"],
        )
        self.assertEqual("chebi", converter.standardize_prefix("chebi"))
        self.assertEqual("chebi", converter.standardize_prefix("CHEBI"))
        self.assertIsNone(converter.standardize_prefix("nope"))

        rows = [
            ("chebi", "CHEBI:1", "http://purl.obolibrary.org/obo/CHEBI_1"),
            ("CHEBI", "CHEBI:2", "https://bioregistry.io/chebi:2"),
        ]
        df = pd.DataFrame(rows, columns=["prefix", "curie", "uri"])
        converter.pd_standardize_prefix(df, column="prefix")
        self.assertEqual(["chebi", "chebi"], list(df["prefix"]), msg=f"\n\n{df}")

        converter.pd_standardize_curie(df, column="curie")
        self.assertEqual(["chebi:1", "chebi:2"], list(df["curie"]))

        converter.pd_standardize_uri(df, column="uri")
        self.assertEqual(
            ["http://purl.obolibrary.org/obo/CHEBI_1", "http://purl.obolibrary.org/obo/CHEBI_2"],
            list(df["uri"]),
        )

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

    def test_incremental(self):
        """Test building a converter from an incremental interface."""
        converter = Converter([])
        for prefix, uri_prefix in self.simple_obo_prefix_map.items():
            converter.add_prefix(prefix, uri_prefix)
        converter.add_prefix(
            "hgnc",
            "https://bioregistry.io/hgnc:",
            prefix_synonyms=["HGNC"],
            uri_prefix_synonyms=["https://identifiers.org/hgnc:"],
        )
        self._assert_convert(converter)
        self.assertEqual(
            "hgnc:1234",
            converter.compress("https://bioregistry.io/hgnc:1234"),
        )
        self.assertEqual(
            "hgnc:1234",
            converter.compress("https://identifiers.org/hgnc:1234"),
        )
        self.assertEqual("https://bioregistry.io/hgnc:1234", converter.expand("HGNC:1234"))

        with self.assertRaises(ValueError):
            converter.add_prefix("GO", "...")
        with self.assertRaises(ValueError):
            converter.add_prefix("...", "http://purl.obolibrary.org/obo/GO_")
        with self.assertRaises(ValueError):
            converter.add_prefix(
                "...", "...", uri_prefix_synonyms=["http://purl.obolibrary.org/obo/GO_"]
            )
        with self.assertRaises(ValueError):
            converter.add_prefix("...", "...", prefix_synonyms=["GO"])

    def test_rdflib(self):
        """Test parsing a converter from an RDFLib object."""
        graph = rdflib.Graph()
        for prefix, uri_prefix in self.simple_obo_prefix_map.items():
            graph.bind(prefix, uri_prefix)
        converter = Converter.from_rdflib(graph)
        self._assert_convert(converter)

        converter_2 = Converter.from_rdflib(graph.namespace_manager)
        self._assert_convert(converter_2)

    def test_expand_all(self):
        """Test expand all."""
        priority_prefix_map = {
            "CHEBI": [
                "http://purl.obolibrary.org/obo/CHEBI_",
                "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:",
            ],
        }
        converter = Converter.from_priority_prefix_map(priority_prefix_map)
        self.assertEqual(
            [
                "http://purl.obolibrary.org/obo/CHEBI_138488",
                "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:138488",
            ],
            converter.expand_all("CHEBI:138488"),
        )
        self.assertIsNone(converter.expand_all("NOPE:NOPE"))


class TestVersion(unittest.TestCase):
    """Trivially test a version."""

    def test_version_type(self):
        """Test the version is a string.

        This is only meant to be an example test.
        """
        version = get_version()
        self.assertIsInstance(version, str)
