"""Tests for data science utilities."""

import unittest

import pandas as pd

import curies


class TestDataScience(unittest.TestCase):
    """Test case for data science utilities."""

    def test_case_mismatch(self):
        """Test case mismatch on CURIE standardizations."""
        data = ["EFO:1", "nope:nope"]
        df = pd.DataFrame([(row,) for row in data], columns=["curie"])

        converter = curies.Converter.from_prefix_map({"efo": "https://identifiers.org/efo:"})
        with self.assertRaises(ValueError):
            converter.pd_standardize_curie(df, column="curie", strict=True)

        results = converter.pd_standardize_curie(df, column="curie")
        suggestions = results.get_suggestions()
        self.assertIsInstance(suggestions, dict)
        self.assertIn("", suggestions)
        # FIXME add more detailed tests
