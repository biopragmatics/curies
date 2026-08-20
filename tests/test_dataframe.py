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
    get_df_unique_prefixes,
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

        with self.assertRaises(ValueError):
            get_filter_df_by_prefixes_index(df, prefixes="a", converter=CONVERTER)

        for method in typing.get_args(PrefixIndexMethod):
            with self.subTest(method=method):
                idx = get_filter_df_by_prefixes_index(
                    df, column=column, prefixes="a", method=method, converter=CONVERTER
                )
                self.assertEqual([0, 1, 2, 3, 4], _rr(idx))

                idx = get_filter_df_by_prefixes_index(
                    df[column], prefixes="a", method=method, converter=CONVERTER
                )
                self.assertEqual([0, 1, 2, 3, 4], _rr(idx))

                idx = get_filter_df_by_prefixes_index(
                    df, column=column, prefixes=["a", "b"], method=method, converter=CONVERTER
                )
                self.assertEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], _rr(idx))

                df_a = filter_df_by_prefixes(df, column=column, prefixes="a")
                self.assertEqual(set(a_curies), set(df_a[column]))

                df_ab = filter_df_by_prefixes(df, column=column, prefixes=["a", "b"])
                self.assertEqual({*a_curies, *b_curies}, set(df_ab[column]))

        df_a1 = filter_df_by_curies(df, column=column, curies="a:1")
        self.assertEqual({"a:1"}, set(df_a1[column]))

        df_a123 = filter_df_by_curies(df, column=column, curies=["a:1", "a:2", "b:1"])
        self.assertEqual({"a:1", "a:2", "b:1"}, set(df_a123[column]))

        prefixes_index = {
            "a": [0, 1, 2, 3, 4],
            "b": [5, 6, 7, 8, 9],
            "c": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        }
        self.assertEqual(prefixes_index, get_df_prefixes_index(df, column=column))
        self.assertEqual(prefixes_index, get_df_prefixes_index(df[column]))

        for curies_index in [
            get_df_curies_index(df, column=column),
            get_df_curies_index(df[column]),
        ]:
            self.assertNotIn("a", curies_index)
            self.assertNotIn("b", curies_index)
            self.assertNotIn("c", curies_index)
            self.assertIn("a:0", curies_index)
            self.assertEqual([0], curies_index["a:0"])
            self.assertEqual([10, 15], curies_index["c:0"])

        self.assertEqual(set("abc"), get_df_unique_prefixes(df, column=column))
        self.assertEqual(set("abc"), get_df_unique_prefixes(df[column]))


def _rr(series: "pd.Series[bool]") -> list[int]:
    return [index for index, value in enumerate(series) if value]
