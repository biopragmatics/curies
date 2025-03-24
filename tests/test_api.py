"""Trivial version test."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import rdflib
from pydantic import ValidationError

import curies
from curies.api import (
    CompressionError,
    Converter,
    CURIEStandardizationError,
    DuplicatePrefixes,
    DuplicateURIPrefixes,
    ExpansionError,
    NamableReference,
    NamedReference,
    NoCURIEDelimiterError,
    PrefixStandardizationError,
    Record,
    Records,
    Reference,
    ReferenceTuple,
    URIStandardizationError,
    chain,
    upgrade_prefix_map,
)
from curies.sources import (
    BIOREGISTRY_CONTEXTS,
    get_bioregistry_converter,
    get_go_converter,
    get_monarch_converter,
    get_obo_converter,
)
from curies.version import get_version
from tests.constants import SLOW

CHEBI_URI_PREFIX = "http://purl.obolibrary.org/obo/CHEBI_"
GO_URI_PREFIX = "http://purl.obolibrary.org/obo/GO_"


class TestStruct(unittest.TestCase):
    """Test the data structures."""

    def test_not_curie(self) -> None:
        """Test a malformed CURIE."""
        with self.assertRaises(NoCURIEDelimiterError) as e:
            Reference.from_curie("not a curie")
        self.assertIn("does not appear to be a CURIE", str(e.exception))

    def test_default_prefix(self) -> None:
        """Test a default (empty) prefix."""
        ref = Reference.from_curie(":something")
        self.assertEqual("", ref.prefix)
        self.assertEqual("something", ref.identifier)

    def test_default_identifier(self) -> None:
        """Test a default (empty) identifier."""
        ref = Reference.from_curie("p1:")
        self.assertEqual("p1", ref.prefix)
        self.assertEqual("", ref.identifier)

    def test_multiple_delimiters(self) -> None:
        """Test a default (empty) identifier."""
        ref = Reference.from_curie("a1:b2:c3")
        self.assertEqual("a1", ref.prefix)
        self.assertEqual("b2:c3", ref.identifier)

    def test_records(self) -> None:
        """Test a list of records."""
        records = Records.model_validate([{"prefix": "chebi", "uri_prefix": CHEBI_URI_PREFIX}])
        converter = Converter(records=records)
        self.assertEqual({"chebi"}, converter.get_prefixes())

    def test_sort(self) -> None:
        """Test sorting."""
        start = [
            Reference.from_curie("def:1234"),
            Reference.from_curie("abc:1234"),
            Reference.from_curie("abc:1235"),
        ]
        expected = [
            Reference.from_curie("abc:1234"),
            Reference.from_curie("abc:1235"),
            Reference.from_curie("def:1234"),
        ]
        self.assertEqual(expected, sorted(start))

    def test_set_membership(self) -> None:
        """Test membership in sets."""
        collection = {
            Reference.from_curie("def:1234"),
            Reference.from_curie("abc:1234"),
            Reference.from_curie("abc:1235"),
        }
        self.assertIn(Reference.from_curie("def:1234"), collection)
        self.assertNotIn(Reference.from_curie("xyz:1234"), collection)
        self.assertNotIn(Reference.from_curie(":1234"), collection)
        self.assertNotIn(Reference.from_curie("abc:"), collection)

    def test_named_set_membership(self) -> None:
        """Test membership in sets of named references."""
        references = {
            NamedReference.from_curie("a:1", "name1"),
            NamedReference.from_curie("a:2", "name2"),
        }
        self.assertIn(Reference.from_curie("a:1"), references)
        self.assertIn(NamableReference.from_curie("a:1"), references)
        self.assertIn(NamedReference.from_curie("a:1", "name1"), references)
        self.assertIn(NamableReference.from_curie("a:1", "name1"), references)
        # the following is a weird case, but shows how this works
        self.assertIn(NamedReference.from_curie("a:1", "name2"), references)

        references_2 = {
            Reference.from_curie("a:1"),
            Reference.from_curie("a:2"),
        }
        self.assertIn(Reference.from_curie("a:1"), references_2)
        self.assertIn(NamableReference.from_curie("a:1", "name1"), references_2)
        self.assertIn(NamedReference.from_curie("a:1", "name1"), references_2)

    def test_tuple(self) -> None:
        """Test reference tuples."""
        t = ReferenceTuple.from_curie("a:1")
        self.assertEqual(Reference(prefix="a", identifier="1"), t.to_pydantic())

    def test_reference_constructor(self) -> None:
        """Test constructing a reference."""
        r1 = Reference(prefix="a", identifier="1")
        r2 = NamableReference(prefix="a", identifier="2")
        r3 = NamableReference(prefix="a", identifier="3", name="item 3")
        r4 = NamedReference(prefix="a", identifier="4", name="item 4")

        self.assertEqual(Reference(prefix="a", identifier="1"), Reference.from_reference(r1))
        self.assertEqual(Reference(prefix="a", identifier="2"), Reference.from_reference(r2))
        self.assertEqual(Reference(prefix="a", identifier="3"), Reference.from_reference(r3))
        self.assertEqual(Reference(prefix="a", identifier="4"), Reference.from_reference(r4))

        self.assertEqual(
            NamableReference(prefix="a", identifier="1", name=None),
            NamableReference.from_reference(r1),
        )
        self.assertEqual(
            NamableReference(prefix="a", identifier="2", name=None),
            NamableReference.from_reference(r2),
        )
        self.assertEqual(
            NamableReference(prefix="a", identifier="3", name="item 3"),
            NamableReference.from_reference(r3),
        )
        self.assertEqual(
            NamableReference(prefix="a", identifier="4", name="item 4"),
            NamableReference.from_reference(r4),
        )

        with self.assertRaises(TypeError):
            NamedReference.from_reference(r1)
        with self.assertRaises(ValidationError):
            NamedReference.from_reference(r2)
        self.assertEqual(
            NamedReference(prefix="a", identifier="3", name="item 3"),
            NamedReference.from_reference(r3),
        )
        self.assertEqual(
            NamedReference(prefix="a", identifier="4", name="item 4"),
            NamedReference.from_reference(r4),
        )


class TestAddRecord(unittest.TestCase):
    """Test adding records."""

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

    def test_duplicate_failure(self) -> None:
        """Test failure caused by double matching."""
        self.converter.add_prefix("GO", GO_URI_PREFIX)
        with self.assertRaises(ValueError):
            self.converter.add_record(Record(prefix="GO", uri_prefix=CHEBI_URI_PREFIX))

    def test_get_prefix_synonyms(self) -> None:
        """Test getting prefix synonyms."""
        self.assertEqual({self.prefix}, self.converter.get_prefixes())
        self.assertEqual({self.prefix}, self.converter.get_prefixes(include_synonyms=False))
        self.assertEqual(
            {self.prefix, self.prefix_synonym},
            self.converter.get_prefixes(include_synonyms=True),
        )

    def test_get_uri_prefix_synonyms(self) -> None:
        """Test getting URI prefix synonyms."""
        self.assertEqual({self.uri_prefix}, self.converter.get_uri_prefixes())
        self.assertEqual({self.uri_prefix}, self.converter.get_uri_prefixes(include_synonyms=False))
        self.assertEqual(
            {self.uri_prefix, self.uri_prefix_synonym},
            self.converter.get_uri_prefixes(include_synonyms=True),
        )

    def test_extend_on_prefix_match(self) -> None:
        """Test adding a new prefix in merge mode."""
        s1, s2, s3 = "s1", "s2", "s3"
        for record in [
            Record(
                prefix="CHEBI",
                prefix_synonyms=[s1],
                uri_prefix=s2,
                uri_prefix_synonyms=[s3],
            ),
            Record(
                prefix=s1,
                prefix_synonyms=["CHEBI"],
                uri_prefix=s2,
                uri_prefix_synonyms=[s3],
            ),
        ]:
            with self.assertRaises(ValueError):
                self.converter.add_record(record, merge=False)
            self.converter.add_record(record, merge=True)
            self.assertEqual(1, len(self.converter.records))
            record = self.converter.records[0]
            self.assertEqual("CHEBI", record.prefix)
            self.assertEqual({s1, self.prefix_synonym}, set(record.prefix_synonyms))
            self.assertEqual(CHEBI_URI_PREFIX, record.uri_prefix)
            self.assertEqual({s2, s3, self.uri_prefix_synonym}, set(record.uri_prefix_synonyms))

    def test_extend_on_uri_prefix_match(self) -> None:
        """Test adding a new prefix in merge mode."""
        s1, s2, s3 = "s1", "s2", "s3"
        for record in [
            Record(
                prefix=s1,
                prefix_synonyms=[s3],
                uri_prefix=s2,
                uri_prefix_synonyms=[CHEBI_URI_PREFIX],
            ),
            Record(
                prefix=s1,
                prefix_synonyms=[s3],
                uri_prefix=CHEBI_URI_PREFIX,
                uri_prefix_synonyms=[s2],
            ),
        ]:
            with self.assertRaises(ValueError):
                self.converter.add_record(record, merge=False)
            self.converter.add_record(record, merge=True)
            self.assertEqual(1, len(self.converter.records))
            record = self.converter.records[0]
            self.assertEqual("CHEBI", record.prefix)
            self.assertEqual({s1, s3, self.prefix_synonym}, set(record.prefix_synonyms))
            self.assertEqual(CHEBI_URI_PREFIX, record.uri_prefix)
            self.assertEqual({s2, self.uri_prefix_synonym}, set(record.uri_prefix_synonyms))

    def test_extend_on_prefix_synonym_match(self) -> None:
        """Test adding a new prefix in merge mode."""
        s1, s2, s3 = "s1", "s2", "s3"
        for record in [
            Record(
                prefix=self.prefix_synonym,
                prefix_synonyms=[s1],
                uri_prefix=s2,
                uri_prefix_synonyms=[s3],
            ),
            Record(
                prefix=s1,
                prefix_synonyms=[self.prefix_synonym],
                uri_prefix=s2,
                uri_prefix_synonyms=[s3],
            ),
        ]:
            self.converter.add_record(record, merge=True)
            self.assertEqual(1, len(self.converter.records))
            record = self.converter.records[0]
            self.assertEqual("CHEBI", record.prefix)
            self.assertEqual({s1, self.prefix_synonym}, set(record.prefix_synonyms))
            self.assertEqual(CHEBI_URI_PREFIX, record.uri_prefix)
            self.assertEqual({s2, s3, self.uri_prefix_synonym}, set(record.uri_prefix_synonyms))

    def test_extend_on_uri_prefix_synonym_match(self) -> None:
        """Test adding a new prefix in merge mode."""
        s1, s2, s3 = "s1", "s2", "s3"
        for record in [
            Record(
                prefix=s1,
                prefix_synonyms=[s2],
                uri_prefix=self.uri_prefix_synonym,
                uri_prefix_synonyms=[s3],
            ),
            Record(
                prefix=s1,
                prefix_synonyms=[s2],
                uri_prefix=s3,
                uri_prefix_synonyms=[self.uri_prefix_synonym],
            ),
        ]:
            self.converter.add_record(record, merge=True)
            self.assertEqual(1, len(self.converter.records))
            record = self.converter.records[0]
            self.assertEqual("CHEBI", record.prefix)
            self.assertEqual({s1, s2, self.prefix_synonym}, set(record.prefix_synonyms))
            self.assertEqual(CHEBI_URI_PREFIX, record.uri_prefix)
            self.assertEqual({s3, self.uri_prefix_synonym}, set(record.uri_prefix_synonyms))

    def test_extend_on_prefix_match_ci(self) -> None:
        """Test adding a new prefix in merge mode."""
        s1, s2, s3 = "s1", "s2", "s3"
        record = Record(
            prefix="chebi", prefix_synonyms=[s1], uri_prefix=s2, uri_prefix_synonyms=[s3]
        )
        self.converter.add_record(record, case_sensitive=False, merge=True)
        self.assertEqual(1, len(self.converter.records))
        record = self.converter.records[0]
        self.assertEqual("CHEBI", record.prefix)
        self.assertEqual({"chebi", s1, self.prefix_synonym}, set(record.prefix_synonyms))
        self.assertEqual(CHEBI_URI_PREFIX, record.uri_prefix)
        self.assertEqual({s2, s3, self.uri_prefix_synonym}, set(record.uri_prefix_synonyms))


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

    def test_reference_tuple(self) -> None:
        """Test the reference tuple data type."""
        t = ReferenceTuple("chebi", "1234")
        self.assertEqual("chebi:1234", t.curie)
        self.assertEqual(t, ReferenceTuple.from_curie("chebi:1234"))

    def test_reference_pydantic(self) -> None:
        """Test the reference Pydantic model."""
        t = Reference(prefix="chebi", identifier="1234")
        self.assertEqual("chebi:1234", t.curie)
        self.assertEqual(t, Reference.from_curie("chebi:1234"))

    def test_invalid_record(self) -> None:
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

    def test_invalid_records(self) -> None:
        """Test throwing an error for duplicated URI prefixes."""
        with self.assertRaises(DuplicateURIPrefixes) as e:
            curies.load_prefix_map(
                {
                    "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
                    "nope": "http://purl.obolibrary.org/obo/CHEBI_",
                }
            )
        self.assertIsInstance(str(e.exception), str)
        with self.assertRaises(DuplicatePrefixes) as e2:
            Converter(
                [
                    Record(prefix="chebi", uri_prefix="https://bioregistry.io/chebi:"),
                    Record(prefix="chebi", uri_prefix="http://purl.obolibrary.org/obo/CHEBI_"),
                ],
            )
        self.assertIsInstance(str(e2.exception), str)

        # No failure
        Converter.from_prefix_map(
            {
                "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
                "nope": "http://purl.obolibrary.org/obo/CHEBI_",
            },
            strict=False,
        )

    def test_subset(self) -> None:
        """Test subsetting a converter."""
        new_converter = self.converter.get_subconverter(["CHEBI"])
        self.assertEqual(1, len(new_converter.records))
        self.assertEqual({"CHEBI"}, new_converter.get_prefixes())
        self.assertEqual(
            {"http://purl.obolibrary.org/obo/CHEBI_"}, new_converter.get_uri_prefixes()
        )
        self.assertEqual({"CHEBI"}, set(new_converter.bimap))
        self.assertEqual({"CHEBI"}, set(new_converter.prefix_map))
        self.assertEqual(
            {"http://purl.obolibrary.org/obo/CHEBI_"}, set(new_converter.reverse_prefix_map)
        )

    def test_empty_subset(self) -> None:
        """Test subsetting a converter and getting an empty one back."""
        new_converter_2 = self.converter.get_subconverter(["NOPE"])
        self.assertEqual(0, len(new_converter_2.records))

    def test_predicates(self) -> None:
        """Add tests for predicates."""
        self.assertFalse(self.converter.is_uri(""))
        self.assertFalse(self.converter.is_uri("nope"))
        self.assertFalse(self.converter.is_curie(""))
        self.assertFalse(self.converter.is_curie("nope"))
        self.assertFalse(self.converter.is_curie(":nope"))
        self.assertFalse(self.converter.is_curie("nope:"))

    def test_convert(self) -> None:
        """Test compression."""
        self.assertEqual({"CHEBI", "MONDO", "GO", "OBO"}, self.converter.get_prefixes())
        self.assertEqual(
            {
                "http://purl.obolibrary.org/obo/CHEBI_",
                "http://purl.obolibrary.org/obo/MONDO_",
                "http://purl.obolibrary.org/obo/GO_",
                "http://purl.obolibrary.org/obo/",
            },
            self.converter.get_uri_prefixes(),
        )
        self._assert_convert(self.converter)

    def _assert_convert(self, converter: Converter) -> None:
        self.assertIn("GO", converter.prefix_map)
        self.assertIn("GO", converter.bimap)
        self.assertIn("GO", converter.reverse_bimap.values())
        self.assertIn("http://purl.obolibrary.org/obo/GO_", converter.reverse_prefix_map)
        self.assertIn("http://purl.obolibrary.org/obo/GO_", converter.reverse_bimap)
        self.assertIn("http://purl.obolibrary.org/obo/GO_", converter.trie)
        self.assertIn("http://purl.obolibrary.org/obo/GO_", converter.bimap.values())
        for curie, uri in [
            ("CHEBI:1", "http://purl.obolibrary.org/obo/CHEBI_1"),
            ("OBO:unnamespaced", "http://purl.obolibrary.org/obo/unnamespaced"),
        ]:
            self.assertTrue(converter.is_uri(uri))
            self.assertTrue(converter.is_curie(curie))
            self.assertFalse(converter.is_curie(uri))
            self.assertFalse(converter.is_uri(curie))
            self.assertEqual(curie, converter.compress(uri))
            self.assertEqual(curie, converter.compress_strict(uri))
            self.assertEqual(uri, converter.expand(curie))
            self.assertEqual(uri, converter.expand_strict(curie))

        self.assertIsNone(converter.compress("http://example.org/missing:00000"))
        self.assertEqual(
            "http://example.org/missing:00000",
            converter.compress("http://example.org/missing:00000", passthrough=True),
        )
        with self.assertRaises(CompressionError):
            converter.compress_strict("http://example.org/missing:00000")

        self.assertIsNone(converter.expand("missing:00000"))
        self.assertEqual("missing:00000", converter.expand("missing:00000", passthrough=True))
        with self.assertRaises(ExpansionError):
            converter.expand_strict("missing:00000")

        self.assertLess(0, len(converter.records), msg="converter has no records")
        self.assertIsNone(converter.get_record("nope"))
        self.assertIsNone(converter.get_record("go"), msg="synonym lookup is not allowed here")
        record = converter.get_record("GO", strict=True)
        self.assertIsNotNone(record, msg=f"records: {[r.prefix for r in converter.records]}")
        self.assertIsInstance(record, Record)
        self.assertEqual("GO", record.prefix)

    @SLOW
    def test_bioregistry(self) -> None:
        """Test loading a remote JSON-LD context."""
        for web in [True, False]:
            bioregistry_converter = get_bioregistry_converter(web=web)
            self.assert_bioregistry_converter(bioregistry_converter)

        c = Converter.from_reverse_prefix_map(f"{BIOREGISTRY_CONTEXTS}/bioregistry.rpm.json")
        self.assertIn("chebi", c.prefix_map)
        self.assertNotIn("CHEBI", c.prefix_map)

    def test_jsonld(self) -> None:
        """Test parsing JSON-LD context."""
        context = {
            "@context": {
                "@version": "1.0.0",  # should skip this
                "": "",  # should skip this
                "hello": "https://example.org/hello:",
                "CHEBI": {
                    "@prefix": True,
                    "@id": "http://purl.obolibrary.org/CHEBI_",
                },
                "nope": {
                    "nope": "nope",
                },
            },
        }
        converter = Converter.from_jsonld(context)
        self.assertIn("hello", converter.prefix_map)
        self.assertIn("CHEBI", converter.prefix_map)

    @SLOW
    def test_from_github(self) -> None:
        """Test getting a JSON-LD map from GitHub."""
        with self.assertRaises(ValueError):
            # missing end .jsonld file
            Converter.from_jsonld_github("biopragmatics", "bioregistry")

        semweb_converter = Converter.from_jsonld_github(
            "biopragmatics", "bioregistry", "exports", "contexts", "semweb.context.jsonld"
        )
        self.assertIn("rdf", semweb_converter.prefix_map)

    @SLOW
    def test_obo(self) -> None:
        """Test the OBO converter."""
        obo_converter = get_obo_converter()
        self.assertIn("CHEBI", obo_converter.prefix_map)
        self.assertNotIn("chebi", obo_converter.prefix_map)

    @SLOW
    def test_monarch(self) -> None:
        """Test the Monarch converter."""
        monarch_converter = get_monarch_converter()
        self.assertIn("CHEBI", monarch_converter.prefix_map)
        self.assertNotIn("chebi", monarch_converter.prefix_map)

    @SLOW
    def test_go_registry(self) -> None:
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
        self.assertIn("chebi", converter.bimap)
        # Synonyms that are non-conflicting also get added
        self.assertIn("CHEBI", converter.prefix_map)
        self.assertNotIn("CHEBI", converter.bimap)
        chebi_uri = converter.prefix_map["chebi"]
        self.assertIn(chebi_uri, converter.reverse_prefix_map)
        self.assertEqual("chebi", converter.reverse_prefix_map[chebi_uri])

    def test_load_path(self) -> None:
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

    def test_reverse_constructor(self) -> None:
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

    def test_standardize_curie(self) -> None:
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
        self.assertEqual("NOPE:NOPE", converter.standardize_curie("NOPE:NOPE", passthrough=True))
        with self.assertRaises(CURIEStandardizationError):
            converter.standardize_curie("NOPE:NOPE", strict=True)

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
        self.assertEqual("NOPE", converter.standardize_uri("NOPE", passthrough=True))
        with self.assertRaises(URIStandardizationError):
            converter.standardize_uri("NOPE:NOPE", strict=True)

    def test_combine(self) -> None:
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

        self.assertEqual("CHEBI", converter.get_record("CHEBI").prefix)
        for url in [
            "http://purl.obolibrary.org/obo/CHEBI_138488",
            "https://bioregistry.io/chebi:138488",
            "http://identifiers.org/chebi/138488",
            "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=138488",
        ]:
            self.assertEqual("CHEBI:138488", converter.compress(url))

        self.assertEqual("GO", converter.get_record("GO").prefix)
        self.assertEqual(
            "GO:0000001",
            converter.compress("http://purl.obolibrary.org/obo/GO_0000001"),
        )

        self.assertEqual(
            "http://purl.obolibrary.org/obo/CHEBI_", converter.get_record("CHEBI").uri_prefix
        )
        self.assertIn("CHEBI", converter.prefix_map)
        self.assertEqual("http://purl.obolibrary.org/obo/CHEBI_", converter.prefix_map["CHEBI"])
        self.assertEqual(
            "http://purl.obolibrary.org/obo/CHEBI_138488",
            converter.expand("CHEBI:138488"),
        )
        self.assertNotIn("nope", converter.get_prefixes())

    def test_combine_with_synonyms(self) -> None:
        """Test combination with synonyms."""
        r1 = Record(prefix="GO", uri_prefix=GO_URI_PREFIX)
        r2 = Record(prefix="go", prefix_synonyms=["GO"], uri_prefix="https://identifiers.org/go:")

        c1 = Converter([])
        c1.add_record(r1)
        self.assertEqual(c1.records, Converter([r1]).records)

        c1.add_record(r2, merge=True)
        self.assertEqual(1, len(c1.records))
        r = c1.records[0]
        self.assertEqual("GO", r.prefix)
        self.assertEqual({"go"}, set(r.prefix_synonyms))
        self.assertEqual("http://purl.obolibrary.org/obo/GO_", r.uri_prefix)
        self.assertEqual({"https://identifiers.org/go:"}, set(r.uri_prefix_synonyms))

        c3 = chain([Converter([r1]), Converter([r2])])
        self.assertEqual(1, len(c3.records))
        self.assertIn("GO", c3.prefix_map)
        self.assertIn("go", c3.prefix_map, msg=f"PM: {c3.prefix_map}")
        self.assertNotIn("go", c3.bimap)
        self.assertIn("GO", c3.bimap)

    def test_combine_ci(self) -> None:
        """Test combining case-insensitive."""
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
        self.assertEqual({"CHEBI"}, converter.get_prefixes(include_synonyms=False))
        self.assertEqual({"CHEBI", "chebi"}, converter.get_prefixes(include_synonyms=True))
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

    def test_combine_with_patterns(self) -> None:
        """Test chaining with patterns."""
        c1 = Converter([Record(prefix="a", uri_prefix="https://example.org/a/", pattern="^\\d{7}")])
        c2 = Converter([Record(prefix="a", uri_prefix="https://example.org/a/", pattern="^\\d+")])
        converter = chain([c1, c2])
        self.assertEqual(
            [Record(prefix="a", uri_prefix="https://example.org/a/", pattern="^\\d{7}")],
            converter.records,
        )

    def test_combine_with_patterns_via_synonym(self) -> None:
        """Test chaining with patterns."""
        c1 = Converter([Record(prefix="a", uri_prefix="https://example.org/a/", pattern="^\\d{7}")])
        c2 = Converter(
            [
                Record(
                    prefix="b",
                    prefix_synonyms=["a"],
                    uri_prefix="https://example.org/b/",
                    pattern="^\\d+",
                )
            ]
        )
        converter = chain([c1, c2])
        self.assertEqual(
            [
                Record(
                    prefix="a",
                    prefix_synonyms=["b"],
                    uri_prefix="https://example.org/a/",
                    uri_prefix_synonyms=["https://example.org/b/"],
                    pattern="^\\d{7}",
                )
            ],
            converter.records,
        )

    def test_df_bulk(self) -> None:
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

    def test_df_standardize(self) -> None:
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
        self.assertEqual("nope", converter.standardize_prefix("nope", passthrough=True))
        with self.assertRaises(PrefixStandardizationError):
            converter.standardize_prefix("nope", strict=True)

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

    def test_file_bulk(self) -> None:
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
                        print(*row, sep="\t", file=file)

                idx = 1 if header else 0

                self.converter.file_expand(path, 0, header=header)
                lines = [line.strip().split("\t") for line in path.read_text().splitlines()]
                self.assertEqual("http://purl.obolibrary.org/obo/CHEBI_1", lines[idx][0])

                self.converter.file_compress(path, 0, header=header)
                lines = [line.strip().split("\t") for line in path.read_text().splitlines()]
                self.assertEqual("CHEBI:1", lines[idx][0])

    def test_incremental(self) -> None:
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

    def test_rdflib(self) -> None:
        """Test parsing a converter from an RDFLib object."""
        graph = rdflib.Graph()
        for prefix, uri_prefix in self.simple_obo_prefix_map.items():
            graph.bind(prefix, uri_prefix)
        converter = Converter.from_rdflib(graph)
        self._assert_convert(converter)

        converter_2 = Converter.from_rdflib(graph.namespace_manager)
        self._assert_convert(converter_2)

    def test_parse_curie(self) -> None:
        """Tests for parse CURIE."""
        converter = Converter(
            records=[
                Record(
                    prefix="GO",
                    uri_prefix="http://purl.obolibrary.org/obo/GO_",
                    prefix_synonyms=["go"],
                )
            ]
        )
        self.assertEqual(
            ReferenceTuple("GO", "1234567"), converter.parse_curie("GO:1234567", strict=True)
        )
        self.assertEqual(
            ReferenceTuple("GO", "1234567"), converter.parse_curie("GO:1234567", strict=False)
        )
        self.assertEqual(
            ReferenceTuple("GO", "1234567"), converter.parse_curie("go:1234567", strict=True)
        )
        self.assertEqual(
            ReferenceTuple("GO", "1234567"), converter.parse_curie("go:1234567", strict=False)
        )

        self.assertIsNone(converter.parse_curie("NOPE:NOPE", strict=False))
        with self.assertRaises(PrefixStandardizationError):
            converter.parse_curie("NOPE:NOPE", strict=True)

    def test_parse(self) -> None:
        """Test parsing URI or CURIE."""
        converter = Converter(
            records=[
                Record(
                    prefix="GO",
                    uri_prefix="http://purl.obolibrary.org/obo/GO_",
                    prefix_synonyms=["go"],
                    uri_prefix_synonyms=["https://identifiers.org/GO:"],
                )
            ]
        )
        curie = "GO:1234567"
        curie2 = "go:1234567"
        uri = "http://purl.obolibrary.org/obo/GO_1234567"
        uri2 = "https://identifiers.org/GO:1234567"

        for s in [curie, curie2, uri, uri2]:
            self.assertEqual(ReferenceTuple("GO", "1234567"), converter.parse(s, strict=True))
            self.assertEqual(ReferenceTuple("GO", "1234567"), converter.parse(s, strict=False))

        # test invalid CURIE parsing
        self.assertIsNone(converter.parse("NOPE:NOPE", strict=False))
        with self.assertRaises(ValueError):
            converter.parse_uri("NOPE:NOPE", strict=True)

        # test invalid URI parsing
        self.assertIsNone(converter.parse("https://example.org/nope", strict=False))
        with self.assertRaises(ValueError):
            converter.parse_uri("https://example.org/nope", strict=True)

        # test whatever's left
        self.assertIsNone(converter.parse("1234567", strict=False))
        with self.assertRaises(ValueError):
            converter.parse_uri("1234567", strict=True)

    def test_compress_or_standardize(self) -> None:
        """Test standardizing URI or CURIE."""
        converter = Converter(
            records=[
                Record(
                    prefix="GO",
                    uri_prefix="http://purl.obolibrary.org/obo/GO_",
                    prefix_synonyms=["go"],
                    uri_prefix_synonyms=["https://identifiers.org/GO:"],
                )
            ]
        )
        curie = "GO:1234567"
        curie2 = "go:1234567"
        uri = "http://purl.obolibrary.org/obo/GO_1234567"
        uri2 = "https://identifiers.org/GO:1234567"

        for s in [curie, curie2, uri, uri2]:
            self.assertEqual(
                "GO:1234567", converter.compress_or_standardize(s, strict=True, passthrough=True)
            )
            self.assertEqual(
                "GO:1234567", converter.compress_or_standardize(s, strict=False, passthrough=True)
            )
            self.assertEqual(
                "GO:1234567", converter.compress_or_standardize(s, strict=True, passthrough=False)
            )
            self.assertEqual(
                "GO:1234567", converter.compress_or_standardize(s, strict=False, passthrough=False)
            )

        self.assertIsNone(
            converter.compress_or_standardize("NOPE:NOPE", strict=False, passthrough=False)
        )
        self.assertEqual(
            "NOPE:NOPE",
            converter.compress_or_standardize("NOPE:NOPE", strict=False, passthrough=True),
        )
        with self.assertRaises(ValueError):
            converter.compress_or_standardize("NOPE:NOPE", strict=True, passthrough=True)
        with self.assertRaises(ValueError):
            converter.compress_or_standardize("NOPE:NOPE", strict=True, passthrough=False)

    def test_parse_uri(self) -> None:
        """Tests for parsing URIs."""
        converter = Converter(
            records=[
                Record(
                    prefix="GO",
                    uri_prefix="http://purl.obolibrary.org/obo/GO_",
                    prefix_synonyms=["go"],
                    uri_prefix_synonyms=["https://identifiers.org/GO:"],
                )
            ]
        )
        uri = "http://purl.obolibrary.org/obo/GO_1234567"
        uri2 = "https://identifiers.org/GO:1234567"

        self.assertEqual(ReferenceTuple("GO", "1234567"), converter.parse_uri(uri, strict=True))
        self.assertEqual(ReferenceTuple("GO", "1234567"), converter.parse_uri(uri, strict=False))

        self.assertEqual(ReferenceTuple("GO", "1234567"), converter.parse_uri(uri2, strict=True))
        self.assertEqual(ReferenceTuple("GO", "1234567"), converter.parse_uri(uri2, strict=False))

        self.assertEqual(
            (None, None), converter.parse_uri("123345", strict=False, return_none=False)
        )
        self.assertIsNone(converter.parse_uri("123345", strict=False, return_none=True))
        with self.assertRaises(ValueError):
            converter.parse_uri("123345", strict=True)

    def test_expand(self) -> None:
        """Tests for expand."""
        converter = Converter(
            records=[
                Record(
                    prefix="GO",
                    uri_prefix="http://purl.obolibrary.org/obo/GO_",
                    prefix_synonyms=["go"],
                )
            ]
        )
        uri = "http://purl.obolibrary.org/obo/GO_1234567"
        self.assertEqual(uri, converter.expand("GO:1234567", strict=True, passthrough=True))
        self.assertEqual(uri, converter.expand("GO:1234567", strict=False, passthrough=True))
        self.assertEqual(uri, converter.expand("GO:1234567", strict=True, passthrough=False))
        self.assertEqual(uri, converter.expand("GO:1234567", strict=False, passthrough=False))

        self.assertEqual(uri, converter.expand("go:1234567", strict=True, passthrough=True))
        self.assertEqual(uri, converter.expand("go:1234567", strict=False, passthrough=True))
        self.assertEqual(uri, converter.expand("go:1234567", strict=True, passthrough=False))
        self.assertEqual(uri, converter.expand("go:1234567", strict=False, passthrough=False))

        self.assertEqual("NOPE:NOPE", converter.expand("NOPE:NOPE", strict=False, passthrough=True))
        self.assertIsNone(converter.expand("NOPE:NOPE", strict=False, passthrough=False))

        with self.assertRaises(ExpansionError):
            converter.expand("NOPE:NOPE", strict=True, passthrough=True)
        with self.assertRaises(ExpansionError):
            converter.expand("NOPE:NOPE", strict=True, passthrough=False)

    def test_expand_pair_all(self) -> None:
        """Tests for expand."""
        converter = Converter(
            records=[
                Record(
                    prefix="GO",
                    uri_prefix="http://purl.obolibrary.org/obo/GO_",
                    prefix_synonyms=["go"],
                    uri_prefix_synonyms=["https://identifiers.org/GO:"],
                )
            ]
        )
        uris = ["http://purl.obolibrary.org/obo/GO_1234567", "https://identifiers.org/GO:1234567"]
        self.assertEqual(uris, converter.expand_pair_all("GO", "1234567", strict=True))
        self.assertEqual(uris, converter.expand_pair_all("GO", "1234567", strict=False))

        # with synonym as input
        self.assertEqual(uris, converter.expand_pair_all("go", "1234567", strict=True))
        self.assertEqual(uris, converter.expand_pair_all("go", "1234567", strict=False))

        self.assertIsNone(converter.expand_pair_all("NOPE", "NOPE", strict=False))
        with self.assertRaises(ExpansionError):
            converter.expand_pair_all("NOPE", "NOPE", strict=True)

    def test_expand_reference(self) -> None:
        """Tests for expand."""
        converter = Converter(
            records=[
                Record(
                    prefix="GO",
                    uri_prefix="http://purl.obolibrary.org/obo/GO_",
                    prefix_synonyms=["go"],
                )
            ]
        )
        uri = "http://purl.obolibrary.org/obo/GO_1234567"
        ref = ReferenceTuple("GO", "1234567")
        ref2 = ReferenceTuple("go", "1234567")
        nope = ReferenceTuple("NOPE", "NOPE")
        self.assertEqual(uri, converter.expand_reference(ref, strict=True, passthrough=True))
        self.assertEqual(uri, converter.expand_reference(ref, strict=False, passthrough=True))
        self.assertEqual(uri, converter.expand_reference(ref, strict=True, passthrough=False))
        self.assertEqual(uri, converter.expand_reference(ref, strict=False, passthrough=False))

        self.assertEqual(uri, converter.expand_reference(ref2, strict=True, passthrough=True))
        self.assertEqual(uri, converter.expand_reference(ref2, strict=False, passthrough=True))
        self.assertEqual(uri, converter.expand_reference(ref2, strict=True, passthrough=False))
        self.assertEqual(uri, converter.expand_reference(ref2, strict=False, passthrough=False))

        self.assertEqual(
            "NOPE:NOPE", converter.expand_reference(nope, strict=False, passthrough=True)
        )
        self.assertIsNone(converter.expand_reference(nope, strict=False, passthrough=False))

        with self.assertRaises(ExpansionError):
            converter.expand_reference(nope, strict=True, passthrough=True)
        with self.assertRaises(ExpansionError):
            converter.expand_reference(nope, strict=True, passthrough=False)

    def test_expand_all(self) -> None:
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
        with self.assertRaises(PrefixStandardizationError):
            converter.expand_all("NOPE:NOPE", strict=True)

    def test_expand_ambiguous(self) -> None:
        """Test expansion of URI or CURIEs."""
        converter = Converter.from_extended_prefix_map(
            [
                Record(
                    prefix="CHEBI",
                    prefix_synonyms=["chebi"],
                    uri_prefix="http://purl.obolibrary.org/obo/CHEBI_",
                    uri_prefix_synonyms=["https://identifiers.org/chebi:"],
                ),
            ]
        )
        self.assertEqual(
            "http://purl.obolibrary.org/obo/CHEBI_138488",
            converter.expand_or_standardize("CHEBI:138488"),
        )
        self.assertEqual(
            "http://purl.obolibrary.org/obo/CHEBI_138488",
            converter.expand_or_standardize("chebi:138488"),
        )
        self.assertEqual(
            "http://purl.obolibrary.org/obo/CHEBI_138488",
            converter.expand_or_standardize("http://purl.obolibrary.org/obo/CHEBI_138488"),
        )
        self.assertEqual(
            "http://purl.obolibrary.org/obo/CHEBI_138488",
            converter.expand_or_standardize("https://identifiers.org/chebi:138488"),
        )

        self.assertIsNone(converter.expand_or_standardize("missing:0000000"))
        with self.assertRaises(ExpansionError):
            converter.expand_or_standardize("missing:0000000", strict=True)
        self.assertEqual(
            "missing:0000000", converter.expand_or_standardize("missing:0000000", passthrough=True)
        )

        self.assertIsNone(converter.expand_or_standardize("https://example.com/missing:0000000"))
        with self.assertRaises(ExpansionError):
            converter.expand_or_standardize("https://example.com/missing:0000000", strict=True)
        self.assertEqual(
            "https://example.com/missing:0000000",
            converter.expand_or_standardize(
                "https://example.com/missing:0000000", passthrough=True
            ),
        )

    def test_compress_ambiguous(self) -> None:
        """Test compression of URI or CURIEs."""
        converter = Converter.from_extended_prefix_map(
            [
                Record(
                    prefix="CHEBI",
                    prefix_synonyms=["chebi"],
                    uri_prefix="http://purl.obolibrary.org/obo/CHEBI_",
                    uri_prefix_synonyms=["https://identifiers.org/chebi:"],
                ),
            ]
        )
        self.assertEqual("CHEBI:138488", converter.compress_or_standardize("CHEBI:138488"))
        self.assertEqual("CHEBI:138488", converter.compress_or_standardize("chebi:138488"))
        self.assertEqual(
            "CHEBI:138488",
            converter.compress_or_standardize("http://purl.obolibrary.org/obo/CHEBI_138488"),
        )
        self.assertEqual(
            "CHEBI:138488",
            converter.compress_or_standardize("https://identifiers.org/chebi:138488"),
        )

        self.assertIsNone(converter.expand_or_standardize("missing:0000000"))
        with self.assertRaises(ExpansionError):
            converter.expand_or_standardize("missing:0000000", strict=True)
        self.assertEqual(
            "missing:0000000", converter.expand_or_standardize("missing:0000000", passthrough=True)
        )

        self.assertIsNone(converter.expand_or_standardize("https://example.com/missing:0000000"))
        with self.assertRaises(ExpansionError):
            converter.expand_or_standardize("https://example.com/missing:0000000", strict=True)
        self.assertEqual(
            "https://example.com/missing:0000000",
            converter.expand_or_standardize(
                "https://example.com/missing:0000000", passthrough=True
            ),
        )

    def test_standardize_identifier(self) -> None:
        """Test standardizing identifiers."""

        class BananaStripperConverter(Converter):
            """A converter that removes bananas from LUIDs."""

            def standardize_identifier(self, prefix: str, identifier: str) -> str | None:
                """Standardize the identifier by removing a banana and checking it is numeric."""
                norm_identifier = identifier.removeprefix(f"{prefix}:")

                # now, do some validation
                if not norm_identifier.isnumeric():
                    return None

                return norm_identifier

        converter = BananaStripperConverter(
            records=[
                Record(
                    prefix="CHEBI",
                    prefix_synonyms=["chebi"],
                    uri_prefix="http://purl.obolibrary.org/obo/CHEBI_",
                    uri_prefix_synonyms=["https://identifiers.org/chebi:"],
                ),
            ]
        )
        self.assertEqual(ReferenceTuple("CHEBI", "1234"), converter.parse_curie("CHEBI:1234"))
        self.assertEqual(ReferenceTuple("CHEBI", "1234"), converter.parse_curie("chebi:1234"))
        self.assertEqual(ReferenceTuple("CHEBI", "1234"), converter.parse_curie("CHEBI:CHEBI:1234"))
        self.assertEqual(ReferenceTuple("CHEBI", "1234"), converter.parse_curie("chebi:CHEBI:1234"))
        self.assertIsNone(converter.parse_curie("NOPE:NOPE:1234", strict=False))

        self.assertIsNone(converter.parse_curie("CHEBI:nope", strict=False))
        # does not solve the problem of synonyms in the banana, this is specific
        # to the current implementation in this test
        self.assertIsNone(converter.parse_curie("chebi:chebi:1234", strict=False))
        with self.assertRaises(ValueError):
            converter.parse_curie("CHEBI:nope", strict=True)


class TestVersion(unittest.TestCase):
    """Trivially test a version."""

    def test_version_type(self) -> None:
        """Test the version is a string.

        This is only meant to be an example test.
        """
        version = get_version()
        self.assertIsInstance(version, str)


class TestUtils(unittest.TestCase):
    """Test utility functions."""

    def test_clean(self) -> None:
        """Test clean."""
        prefix_map = {
            "b": "https://example.com/a/",
            "a": "https://example.com/a/",
            "c": "https://example.com/c/",
        }
        records = upgrade_prefix_map(prefix_map)
        self.assertEqual(2, len(records))
        a_record, c_record = records

        self.assertEqual("a", a_record.prefix)
        self.assertEqual(["b"], a_record.prefix_synonyms)
        self.assertEqual("https://example.com/a/", a_record.uri_prefix)
        self.assertEqual([], a_record.uri_prefix_synonyms)

        self.assertEqual("c", c_record.prefix)
        self.assertEqual([], c_record.prefix_synonyms)
        self.assertEqual("https://example.com/c/", c_record.uri_prefix)
        self.assertEqual([], c_record.uri_prefix_synonyms)
