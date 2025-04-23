"""Tests for preprocessing converter."""

# coverage erase && coverage run -p -m pytest tests/test_wrapped.py --durations=20 && coverage combine && coverage html && open htmlcov/index.html

import tempfile
import unittest
from pathlib import Path
from typing import ClassVar

from curies import Converter, ReferenceTuple
from curies.preprocessing import (
    BlocklistError,
    PreprocessingBlocklists,
    PreprocessingConverter,
    PreprocessingRewrites,
    PreprocessingRules,
)

EX1_RT = ReferenceTuple("GO", "1234567")
EX1_URI = "http://purl.obolibrary.org/obo/GO_1234567"
EX1_CURIE = "GO:1234567"

DECOY_1_CURIE = "NOPE:NOPE"
DECOY_1_URI = "https://example.org/NOPE/NOPE"


class TestWrapped(unittest.TestCase):
    """Tests for preprocessing converter."""

    rules: ClassVar[PreprocessingRules]
    inner_converter: ClassVar[Converter]
    converter: ClassVar[PreprocessingConverter]
    temporary_directory: ClassVar[tempfile.TemporaryDirectory[str]]
    directory: ClassVar[Path]
    rules_path: ClassVar[Path]

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test case."""
        cls.rules = PreprocessingRules(
            rewrites=PreprocessingRewrites(
                full={
                    "is_a": "rdf:type",
                    "http://creativecommons.org/licenses/by/3.0/": "spdx:CC-BY-3.0",
                },
                prefix={
                    "OMIM:PS": "omim.ps:",
                    "omim:PS": "omim.ps:",
                },
                resource_prefix={
                    "clo": {
                        "j": "NCIT:",
                    },
                },
                resource_full={
                    "clo": {
                        "nopeforever": "NCIT:5678",
                    },
                },
            ),
            blocklists=PreprocessingBlocklists(
                full=["rdf:NOPE"],
                resource_prefix={
                    "chebi": [
                        "pubmed:"
                    ]  # this means that only throw away pubmed references in ChEBI
                },
                resource_full={
                    "chebi": ["omim:1356"],  # in case we just hate this CURIE/URI/string
                },
            ),
        )
        cls.inner_converter = Converter.from_prefix_map(
            {
                "GO": "http://purl.obolibrary.org/obo/GO_",
                "NCIT": "http://purl.obolibrary.org/obo/NCIT_",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "omim": "https://omim.org/MIM:",
                "omim.ps": "https://omim.org/phenotypicSeries/PS",
                "pubmed": "http://rdf.ncbi.nlm.nih.gov/pubchem/reference/",
                "spdx": "https://spdx.org/licenses/",
            }
        )

        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temporary_directory.name)

        # write the rules just so we can test loading from a file
        cls.rules_path = cls.directory.joinpath("rules.json")
        cls.rules_path.write_text(cls.rules.model_dump_json(indent=2, exclude_unset=True))

        cls.converter = PreprocessingConverter.from_converter(
            converter=cls.inner_converter, rules=cls.rules_path
        )

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up the class."""
        cls.temporary_directory.cleanup()

    def test_lint(self) -> None:
        """Run the linting code, just to make sure it works."""
        self.rules.lint_file(self.rules_path)

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
        self.assertEqual(
            ReferenceTuple("spdx", "CC-BY-3.0"),
            self.converter.parse_uri("http://creativecommons.org/licenses/by/3.0/"),
        )

    def test_global_prefix_rewrite(self) -> None:
        """Test global prefix rewrite."""
        self.assertEqual(
            ReferenceTuple("omim.ps", "1234"), self.converter.parse_curie("OMIM:PS1234")
        )

        # test when there's a related rewrite rule, but not used
        self.assertEqual(ReferenceTuple("omim", "1234"), self.converter.parse_curie("omim:1234"))

    def test_resource_full_rewrite(self) -> None:
        """Test global full string rewrite."""
        self.assertIsNone(self.converter.parse("nopeforever"))
        with self.assertRaises(ValueError):
            self.converter.parse_curie("nopeforever")
        self.assertEqual(
            ReferenceTuple("NCIT", "5678"),
            self.converter.parse_curie("nopeforever", context="clo"),
        )

    def test_resource_prefix_rewrite(self) -> None:
        """Test resource-specific prefix rewrite."""
        self.assertEqual(
            ReferenceTuple("NCIT", "1234"),
            self.converter.parse("j1234", context="clo"),
        )

        # when we have rewrite rules for that ontology, but none apply
        self.assertIsNone(self.converter.parse("xyz", context="clo"))

        with self.assertRaises(ValueError):
            self.assertIsNone(self.converter.parse_curie("j1234"))
        with self.assertRaises(ValueError):
            self.assertIsNone(self.converter.parse_curie("j1234", context="chebi"))

    def test_resource_specific_blocklist(self) -> None:
        """Test resource-specific blocklist."""
        self.assertEqual(
            ReferenceTuple("pubmed", "1234"),
            self.converter.parse_curie("pubmed:1234"),
        )
        self.assertEqual(
            ReferenceTuple("pubmed", "1234"),
            self.converter.parse_curie("pubmed:1234", context="doid"),
        )
        with self.assertRaises(BlocklistError):
            self.converter.parse_curie("pubmed:1234", context="chebi")
        self.assertIsNone(
            self.converter.parse_curie("pubmed:1234", context="chebi", block_action="pass")
        )

        self.converter.parse_curie("omim:1234", context="chebi")
        # normally, OMIM works, but we configured a specific one for the blocklist
        with self.assertRaises(BlocklistError):
            self.converter.parse_curie("omim:1356", context="chebi")
        self.assertIsNone(
            self.converter.parse_curie("omim:1356", context="chebi", block_action="pass")
        )

    def test_global_blocklist(self) -> None:
        """Test global blocklist."""
        with self.assertRaises(BlocklistError):
            self.converter.parse("rdf:NOPE")
        self.assertIsNone(self.converter.parse("rdf:NOPE", block_action="pass"))

        with self.assertRaises(BlocklistError):
            self.converter.parse_curie("rdf:NOPE")
        self.assertIsNone(self.converter.parse_curie("rdf:NOPE", block_action="pass"))

        with self.assertRaises(BlocklistError):
            self.converter.parse_uri("rdf:NOPE")
        self.assertIsNone(self.converter.parse_uri("rdf:NOPE", block_action="pass"))
