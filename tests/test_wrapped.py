"""Tests for preprocessing converter."""

# coverage erase && coverage run -p -m pytest tests/test_wrapped.py --durations=20 && coverage combine && coverage html && open htmlcov/index.html

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
                resource_prefix={
                    "clo": {
                        "j": "ncit:",
                    },
                },
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

    def test_global_full_rewrite(self) -> None:
        """Test global full string rewrite."""
        self.assertEqual(ReferenceTuple("rdf", "type"), self.converter.parse("is_a"))
        self.assertEqual(ReferenceTuple("rdf", "type"), self.converter.parse_curie("is_a"))

    def test_global_prefix_rewrite(self) -> None:
        """Test global prefix rewrite."""
        self.assertEqual(
            ReferenceTuple("omim.ps", "1234"), self.converter.parse_curie("OMIM:PS1234")
        )

        # test when there's a related rewrite rule, but not used
        self.assertEqual(ReferenceTuple("omim", "1234"), self.converter.parse_curie("OMIM:1234"))

    def test_resource_prefix_rewrite(self) -> None:
        """Test resource-specific prefix rewrite."""
        self.assertEqual(
            ReferenceTuple("NCIT", "1234"),
            self.converter.parse_curie("j1234", ontology_prefix="clo"),
        )
        self.assertIsNone(self.converter.parse_curie("j1234"))
        self.assertIsNone(self.converter.parse_curie("j1234", ontology_prefix="chebi"))

    def test_resource_specific_blacklist(self) -> None:
        """Test resource-specific blacklist."""
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

    def test_global_blacklist(self) -> None:
        """Test global blacklist."""
        with self.assertRaises(BlacklistError):
            self.converter.parse("rdf:NOPE")
        with self.assertRaises(BlacklistError):
            self.converter.parse_curie("rdf:NOPE")
