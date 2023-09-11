import unittest

import pandas as pd

import curies


class TestDataScience(unittest.TestCase):
    """"""

    def test_case_mismatch(self):
        data = ["EFO:1", "nope:nope"]
        df = pd.DataFrame([(row,) for row in data], columns=["curie"])

        converter = curies.Converter.from_prefix_map({"efo": "https://identifiers.org/efo:"})
        with self.assertRaises(ValueError):
            converter.pd_standardize_curie(df, column="curie", strict=True)

        results = converter.pd_standardize_curie(df, column="curie")
        suggestions = results.get_suggestions()
