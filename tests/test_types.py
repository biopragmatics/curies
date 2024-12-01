"""Test types."""

import unittest

from pydantic import BaseModel, ValidationError

from curies import Converter, Prefix, PrefixMap
from curies.typr import CURIE, URI


class WrappedPrefix(BaseModel):
    """A model wrapping a prefix."""

    prefix: Prefix


class WrappedCURIE(BaseModel):
    """A model wrapping a CURIE."""

    curie: CURIE


class WrappedURI(BaseModel):
    """A model wrapping a URI."""

    uri: URI


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

    def test_curie(self):
        """Test instantiating CURIEs."""
        model_1 = WrappedCURIE.model_validate({"curie": "chebi:1234"})
        self.assertEqual("chebi:1234", model_1.curie)

        model_2 = WrappedCURIE.model_validate({"curie": "CHEBI:1234"})
        self.assertEqual("CHEBI:1234", model_2.curie)

        # Test that a synonym gets standardized properly
        model_3 = WrappedCURIE.model_validate({"curie": "CHEBI:1234"}, context=converter)
        self.assertEqual("CHEBI:1234", model_3.curie)

        # Test that a canonical prefix is passed through
        model_4 = WrappedCURIE.model_validate({"curie": "chebi:1234"}, context=converter)
        self.assertEqual("CHEBI:1234", model_4.curie)

        # Test that a synonym gets standardized properly, when passing context in a dict
        model_5 = WrappedCURIE.model_validate(
            {"curie": "CHEBI:1234"}, context={"converter": converter}
        )
        self.assertEqual("CHEBI:1234", model_5.curie)

        # Test that a canonical prefix is passed through, when passing context in a dict
        model_6 = WrappedCURIE.model_validate(
            {"curie": "chebi:1234"}, context={"converter": converter}
        )
        self.assertEqual("CHEBI:1234", model_6.curie)

        # Test an invalid prefix raises an error, when passing a converter directly
        with self.assertRaises(ValidationError):
            WrappedCURIE.model_validate({"curie": "nope:nope"}, context=converter)

        # Test an invalid prefix raises an error, when passing a converter in a dict
        with self.assertRaises(ValidationError):
            WrappedCURIE.model_validate({"curie": "nope:nope"}, context={"converter": converter})

    def test_uri(self):
        """Test instantiating URIs."""
        canonical = "http://purl.obolibrary.org/obo/CHEBI_1234"
        secondary = "https://identifiers.org/chebi:1234"
        model_1 = WrappedURI.model_validate({"uri": canonical})
        self.assertEqual(canonical, model_1.uri)

        model_2 = WrappedURI.model_validate({"uri": secondary})
        self.assertEqual(secondary, model_2.uri)

        # Test that a synonym gets standardized properly
        model_3 = WrappedURI.model_validate({"uri": canonical}, context=converter)
        self.assertEqual(canonical, model_3.uri)

        # Test that a canonical prefix is passed through
        model_4 = WrappedURI.model_validate({"uri": secondary}, context=converter)
        self.assertEqual(canonical, model_4.uri)

        # Test that a synonym gets standardized properly, when passing context in a dict
        model_5 = WrappedURI.model_validate({"uri": secondary}, context={"converter": converter})
        self.assertEqual(canonical, model_5.uri)

        # Test that a canonical prefix is passed through, when passing context in a dict
        model_6 = WrappedURI.model_validate({"uri": canonical}, context={"converter": converter})
        self.assertEqual(canonical, model_6.uri)

        # Test an invalid prefix raises an error, when passing a converter directly
        with self.assertRaises(ValidationError):
            WrappedURI.model_validate({"uri": "http://example.orc.nope"}, context=converter)

        # Test an invalid prefix raises an error, when passing a converter in a dict
        with self.assertRaises(ValidationError):
            WrappedURI.model_validate(
                {"uri": "http://example.orc.nope"}, context={"converter": converter}
            )
