"""Test dataframe utilities."""

import typing
import unittest

import pandas as pd

from curies import Converter
from curies.dataframe import (
    PrefixIndexMethod,
    filter_df_by_curies,
    filter_df_by_prefixes,
    get_df_curies_index,
    get_df_prefixes_index,
    get_filter_df_by_prefixes_index,
)

CONVERTER = Converter.from_prefix_map(
    {
        "a": "https://example.org/a/",
        "b": "https://example.org/b/",
        "c": "https://example.org/c/",
    }
)


class TestDataframe(unittest.TestCase):
    """A test case for dataframe utilities."""

    def test_get_prefix_index(self) -> None:
        """Test getting a prefix index."""
        column = "curie"
        a_curies = [f"a:{i}" for i in range(5)]
        b_curies = [f"b:{i}" for i in range(5)]
        c_curies = [f"c:{i}" for i in range(5)] * 2
        curies = [*a_curies, *b_curies, *c_curies]
        rows = [(curie,) for curie in curies]
        df = pd.DataFrame(rows, columns=[column])

        for method in typing.get_args(PrefixIndexMethod):
            with self.subTest(method=method):
                idx = get_filter_df_by_prefixes_index(
                    df, column, "a", method=method, converter=CONVERTER
                )
                self.assertEqual([0, 1, 2, 3, 4], _rr(idx))

                idx = get_filter_df_by_prefixes_index(
                    df, column, ["a", "b"], method=method, converter=CONVERTER
                )
                self.assertEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], _rr(idx))

                df_a = filter_df_by_prefixes(df, column, "a")
                self.assertEqual(set(a_curies), set(df_a[column]))

                df_ab = filter_df_by_prefixes(df, column, ["a", "b"])
                self.assertEqual({*a_curies, *b_curies}, set(df_ab[column]))

        df_a1 = filter_df_by_curies(df, column, "a:1")
        self.assertEqual({"a:1"}, set(df_a1[column]))

        df_a123 = filter_df_by_curies(df, column, ["a:1", "a:2", "b:1"])
        self.assertEqual({"a:1", "a:2", "b:1"}, set(df_a123[column]))

        dense_prefix_mapping = get_df_prefixes_index(df, column)
        self.assertEqual(
            {
                "a": [0, 1, 2, 3, 4],
                "b": [5, 6, 7, 8, 9],
                "c": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
            },
            dense_prefix_mapping,
        )

        dense_curie_mapping = get_df_curies_index(df, column)
        self.assertNotIn("a", dense_curie_mapping)
        self.assertNotIn("b", dense_curie_mapping)
        self.assertNotIn("c", dense_curie_mapping)
        self.assertIn("a:0", dense_curie_mapping)
        self.assertEqual([0], dense_curie_mapping["a:0"])
        self.assertEqual([10, 15], dense_curie_mapping["c:0"])


def _rr(series: pd.Series) -> list[int]:
    return [index for index, value in enumerate(series) if value]
