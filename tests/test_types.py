"""Test types."""

import unittest

from pydantic import BaseModel, ValidationError

from curies import Converter, Prefix, PrefixMap


class WrappedPrefix(BaseModel):
    """A model wrapping a prefix."""

    prefix: Prefix


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

    def test_prefix(self):
        """Test instantiating prefixes."""
        model_1 = WrappedPrefix.model_validate({"prefix": "hello"})
        self.assertEqual("hello", model_1.prefix)

        # this doesn't match the regex for prefixes
        with self.assertRaises(ValidationError):
            WrappedPrefix.model_validate({"prefix": "!!!"})

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

    def test_prefix_root_model(self):
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
                    "$": "",
                    "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
                }
            )
