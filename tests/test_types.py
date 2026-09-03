"""Test types."""

import unittest

from pydantic import BaseModel, ValidationError

from curies import Converter, Prefix, PrefixMap, Reference


class WrappedPrefix(BaseModel):
    """A model wrapping a prefix."""

    prefix: Prefix


class WrappedPrefixMap(BaseModel):
    """A model wrapping a prefix map."""

    prefix_map: PrefixMap


class WrappedCURIE(BaseModel):
    """A model wrapping a reference."""

    reference: Reference


converter = Converter.from_extended_prefix_map(
    [
        {
            "prefix": "CHEBI",
            "prefix_synonyms": ["chebi"],
            "uri_prefix": "http://purl.obolibrary.org/obo/CHEBI_",
            "uri_prefix_synonyms": [
                "https://identifiers.org/chebi:",
            ],
        },
    ]
)


class TestTypes(unittest.TestCase):
    """Test types."""

    def test_prefix(self) -> None:
        """Test instantiating prefixes."""
        model_1 = WrappedPrefix.model_validate({"prefix": "hello"})
        self.assertEqual("hello", model_1.prefix)

        model_2 = WrappedPrefix.model_validate({"prefix": "CHEBI"})
        self.assertEqual("CHEBI", model_2.prefix)

        # Test that a synonym gets standardized properly
        model_3 = WrappedPrefix.model_validate({"prefix": "CHEBI"}, context=converter)
        self.assertEqual("CHEBI", model_3.prefix)

        # Test that a canonical prefix is passed through
        model_4 = WrappedPrefix.model_validate({"prefix": "chebi"}, context=converter)
        self.assertEqual("CHEBI", model_4.prefix)

        # Test that a synonym gets standardized properly, when passing context in a dict
        model_5 = WrappedPrefix.model_validate(
            {"prefix": "CHEBI"}, context={"converter": converter}
        )
        self.assertEqual("CHEBI", model_5.prefix)

        # Test that a canonical prefix is passed through, when passing context in a dict
        model_6 = WrappedPrefix.model_validate(
            {"prefix": "chebi"}, context={"converter": converter}
        )
        self.assertEqual("CHEBI", model_6.prefix)

        # Test an invalid prefix raises an error, when passing a converter directly
        with self.assertRaises(ValidationError):
            WrappedPrefix.model_validate({"prefix": "nope"}, context=converter)

        # Test an invalid prefix raises an error, when passing a converter in a dict
        with self.assertRaises(ValidationError):
            WrappedPrefix.model_validate({"prefix": "nope"}, context={"converter": converter})

    def test_prefix_root_model(self) -> None:
        """Test the root model."""
        dd = {
            "": "http://example.org",
            "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        }
        prefix_map = PrefixMap.model_validate(dd)
        self.assertEqual(dd, prefix_map.root)

        prefix_map = PrefixMap.model_validate(
            {
                "chebi": "http://purl.obolibrary.org/obo/CHEBI_",
            },
            context=converter,
        )
        self.assertEqual(
            {
                "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
            },
            prefix_map.root,
        )

        with self.assertRaises(ValidationError):
            PrefixMap.model_validate(
                {
                    "NOPE": "http://purl.obolibrary.org/obo/CHEBI_",
                },
                context=converter,
            )

    def test_prefix_map_wrapped(self) -> None:
        """Test a wrapped prefix map."""
        dd = {
            "prefix_map": {
                "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
            }
        }
        wpm = WrappedPrefixMap.model_validate(dd)
        self.assertIn("CHEBI", wpm.prefix_map.root)

    def test_curie(self) -> None:
        """Test a wrapped CURIE."""
        wpm = WrappedCURIE.model_validate(
            {
                "reference": "CHEBI:1234",
            }
        )
        self.assertIn("CHEBI", wpm.reference.prefix)
        self.assertIn("1234", wpm.reference.identifier)
        self.assertIn("CHEBI:1234", wpm.reference.curie)

        with self.assertRaises(ValidationError):
            WrappedCURIE.model_validate({"reference": "NOPENOPENOPE"})

        dd = {"reference": "CHEBI:1234"}
        wpm = WrappedCURIE.model_validate(dd, context=converter)
        self.assertIn("CHEBI", wpm.reference.prefix)
        self.assertIn("1234", wpm.reference.identifier)
        self.assertIn("CHEBI:1234", wpm.reference.curie)

        with self.assertRaises(ValidationError):
            WrappedCURIE.model_validate({"reference": "MONDO:1234"}, context=converter)
