"""Tests for preprocessing converter."""

import unittest
from typing import ClassVar

from curies import Converter, ReferenceTuple
from curies.wrapped import Blacklist, BlacklistError, PreprocessingConverter, Rewrites, Rules

EX1_RT = ReferenceTuple("GO", "1234567")
EX1_URI = "http://purl.obolibrary.org/obo/GO_1234567"
EX1_CURIE = "GO:1234567"

DECOY_1_CURIE = "NOPE:NOPE"
DECOY_1_URI = "https://example.org/NOPE/NOPE"


class TestWrapped(unittest.TestCase):
    """Tests for preprocessing converter."""

    rules: ClassVar[Rules]
    inner_converter: ClassVar[Converter]
    converter: ClassVar[PreprocessingConverter]

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test case."""
        cls.rules = Rules(
            rewrites=Rewrites(
                full={"is_a": "rdf:type"},
                prefix={"OMIM:PS": "omim.ps:"},
            ),
            blacklists=Blacklist(
                full=["rdf:NOPE"],
                resource_prefix={
                    "chebi": [
                        "pubmed:"
                    ]  # this means that only throw away pubmed references in ChEBI
                },
            ),
        )
        cls.inner_converter = Converter.from_prefix_map(
            {
                "GO": "http://purl.obolibrary.org/obo/GO_",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "omim.ps": "https://omim.org/phenotypicSeries/PS",
                "pubmed": "http://rdf.ncbi.nlm.nih.gov/pubchem/reference/",
            }
        )
        cls.converter = PreprocessingConverter.from_converter(
            converter=cls.inner_converter, rules=cls.rules
        )

    def test_unprocessed(self) -> None:
        """Tests that should be the same for both converters."""
        for converter in (self.inner_converter, self.converter):
            self.assertEqual(EX1_CURIE, converter.compress(EX1_URI))
            self.assertEqual(EX1_URI, converter.expand(EX1_CURIE))
            self.assertEqual(EX1_RT, converter.parse(EX1_URI))
            self.assertEqual(EX1_RT, converter.parse(EX1_CURIE))
            self.assertEqual(EX1_RT, converter.parse_uri(EX1_URI))
            self.assertEqual(EX1_RT, converter.parse_curie(EX1_CURIE))

            self.assertIsNone(converter.compress(DECOY_1_URI))
            self.assertIsNone(converter.expand(DECOY_1_CURIE))
            self.assertIsNone(converter.parse_curie(DECOY_1_CURIE))
            self.assertIsNone(converter.parse_uri(DECOY_1_URI, return_none=True))
            self.assertIsNone(converter.parse(DECOY_1_URI))
            self.assertIsNone(converter.parse(DECOY_1_CURIE))

    def test_preprocessing_converter(self) -> None:
        """Test the preprocessing converter."""
        self.assertEqual(ReferenceTuple("GO", "1234567"), self.converter.parse_curie("GO:1234567"))
        self.assertEqual(
            ReferenceTuple("omim.ps", "1234"), self.converter.parse_curie("OMIM:PS1234")
        )

        # Test full rewrite
        self.assertEqual(ReferenceTuple("rdf", "type"), self.converter.parse("is_a"))

        with self.assertRaises(BlacklistError):
            self.assertIsNone(self.converter.parse("rdf:NOPE"))  # blacklist full

        self.assertEqual(
            ReferenceTuple("pubmed", "1234"),
            self.converter.parse_curie("pubmed:1234"),
        )
        self.assertEqual(
            ReferenceTuple("pubmed", "1234"),
            self.converter.parse_curie("pubmed:1234", ontology_prefix="doid"),
        )
        with self.assertRaises(BlacklistError):
            self.converter.parse_curie("pubmed:1234", ontology_prefix="chebi")

        self.assertIsNone(
            self.converter.parse_curie("http://purl.obolibrary.org/obo/GO_1234567", strict=False)
        )
        with self.assertRaises(ValueError):
            self.converter.parse_curie("http://purl.obolibrary.org/obo/GO_1234567", strict=True)
