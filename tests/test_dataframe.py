"""Test dataframe utilities."""

import typing
import unittest

import pandas as pd

from curies import Converter
from curies.dataframe import Method, get_prefix_index

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
        curies = [
            *(f"a:{i}" for i in range(5)),
            *(f"b:{i}" for i in range(5)),
            *(f"c:{i}" for i in range(5)),
        ]
        rows = [(curie,) for curie in curies]
        df = pd.DataFrame(rows, columns=["curie"])

        for method in typing.get_args(Method):
            with self.subTest(method=method):
                idx = get_prefix_index(df, "curie", "a", method=method, converter=CONVERTER)
                self.assertEqual([0, 1, 2, 3, 4], _rr(idx))

                idx = get_prefix_index(df, "curie", ["a", "b"], method=method, converter=CONVERTER)
                self.assertEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], _rr(idx))


def _rr(series: pd.Series) -> list[int]:
    return [index for index, value in enumerate(series) if value]
