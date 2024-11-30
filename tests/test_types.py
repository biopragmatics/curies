"""Test types."""

import unittest

from pydantic import BaseModel, ValidationError

from curies import Converter
from curies.typr import Prefix


class Wrapped(BaseModel):
    """A model wrapping a prefix."""

    prefix: Prefix


class TestTypes(unittest.TestCase):
    """Test types."""

    def test_prefix(self):
        """Test instantiating prefixes."""
        model_1 = Wrapped.model_validate({"prefix": "hello"})
        self.assertEqual("hello", model_1.prefix)

        # this doesn't match the regex for prefixes
        with self.assertRaises(ValidationError):
            Wrapped.model_validate({"prefix": "!!!"})

        model_2 = Wrapped.model_validate({"prefix": "CHEBI"})
        self.assertEqual("CHEBI", model_2.prefix)

        converter = Converter.from_extended_prefix_map(
            [
                {
                    "prefix": "chebi",
                    "prefix_synonyms": ["CHEBI"],
                    "uri_prefix": "http://purl.obolibary.org/obo/CHEBI_",
                }
            ]
        )

        # Test that a synonym gets standardized properly
        model_3 = Wrapped.model_validate({"prefix": "CHEBI"}, context=converter)
        self.assertEqual("chebi", model_3.prefix)

        # Test that a canonical prefix is passed through
        model_4 = Wrapped.model_validate({"prefix": "chebi"}, context=converter)
        self.assertEqual("chebi", model_4.prefix)

        # Test that a synonym gets standardized properly, when passing context in a dict
        model_5 = Wrapped.model_validate({"prefix": "CHEBI"}, context={"converter": converter})
        self.assertEqual("chebi", model_5.prefix)

        # Test that a canonical prefix is passed through, when passing context in a dict
        model_6 = Wrapped.model_validate({"prefix": "chebi"}, context={"converter": converter})
        self.assertEqual("chebi", model_6.prefix)

        # Test an invalid prefix raises an error, when passing a converter directly
        with self.assertRaises(ValidationError):
            Wrapped.model_validate({"prefix": "nope"}, context=converter)

        # Test an invalid prefix raises an error, when passing a converter in a dict
        with self.assertRaises(ValidationError):
            Wrapped.model_validate({"prefix": "nope"}, context={"converter": converter})
