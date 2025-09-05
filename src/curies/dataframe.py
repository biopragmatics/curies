"""Dataframe operations."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection
from typing import TYPE_CHECKING, Callable, Literal, Union

from typing_extensions import TypeAlias

from .utils import _prefix_from_curie

if TYPE_CHECKING:
    import pandas as pd

    from .api import Converter

__all__ = [
    "PrefixIndexMethod",
    "filter_df_by_curies",
    "filter_df_by_prefixes",
    "get_df_curies_index",
    "get_df_prefixes_index",
    "get_df_unique_prefixes",
    "get_filter_df_by_curies_index",
    "get_filter_df_by_prefixes_index",
]

DataframeOrSeries: TypeAlias = Union["pd.DataFrame", "pd.Series[str]"]


def _get_prefix_checker(prefix: str | Collection[str]) -> Callable[[str], bool]:
    """Get a function that checks if a CURIE starts with a prefix."""
    if isinstance(prefix, str):
        prefix_with_colon = prefix + ":"

        def _func(curie: str) -> bool:
            return curie.startswith(prefix_with_colon)

    else:
        prefixes_with_colons = {p + ":" for p in prefix}

        def _func(curie: str) -> bool:
            return any(
                curie.startswith(prefix_with_colon) for prefix_with_colon in prefixes_with_colons
            )

    return _func


def _get_prefixes_from_curie_column(
    df: DataframeOrSeries,
    *,
    column: int | str | None = None,
    converter: Converter | None = None,
    validate: bool,
) -> pd.Series[str]:
    return _get_series(df, column).map(_get_curie_parser(converter=converter, validate=validate))


def _get_curie_parser(
    *, converter: Converter | None = None, validate: bool = False
) -> Callable[[str], str]:
    # TODO what if it can't parse?
    # TODO handle None?
    # TODO handle invalid CURIEs?

    if not validate:
        return _prefix_from_curie
    elif converter is None:
        raise ValueError("converter is required for validation")
    else:

        def _func(curie: str) -> str:
            reference = converter.parse_curie(curie, strict=True)
            return reference.prefix

    return _func


#: The method for filtering on prefixe
PrefixIndexMethod: TypeAlias = Literal["iterative", "precalculated"]


def get_filter_df_by_prefixes_index(
    df: DataframeOrSeries,
    *,
    column: str | int | None = None,
    prefixes: str | Collection[str],
    method: PrefixIndexMethod | None = None,
    converter: Converter | None = None,
    validate: bool = False,
) -> pd.Series[bool]:
    """Get an index of CURIEs in the given column that start with the prefix(es)."""
    if method == "iterative" or method is None:
        return _get_series(df, column).map(_get_prefix_checker(prefixes))
    elif method == "precalculated":
        if converter is None:  # pragma: no cover
            raise ValueError("a converter is required for method B")
        prefix_series = _get_prefixes_from_curie_column(
            df, column=column, converter=converter, validate=validate
        )
        if isinstance(prefixes, str):
            return prefix_series == prefixes
        else:
            return prefix_series.isin(prefixes)
    else:  # pragma: no cover
        raise ValueError(f"invalid method given: {method}")


def filter_df_by_prefixes(
    df: pd.DataFrame,
    *,
    column: str | int,
    prefixes: str | Collection[str],
    method: PrefixIndexMethod | None = None,
    converter: Converter | None = None,
) -> pd.DataFrame:
    """Filter a dataframe based on CURIEs in a given column having a given prefix or set of prefixes.

    :param df: A dataframe
    :param column: The integer index or column name of a column containing CURIEs
    :param prefixes: The prefix (given as a string) or collection of prefixes (given as a
        list, set, etc.) to keep
    :param method: The implementation for getting the prefix index
    :param converter: A converter

    :returns: If not in place, return a new dataframe.
    """
    idx = get_filter_df_by_prefixes_index(
        df=df, column=column, prefixes=prefixes, method=method, converter=converter
    )
    return df[idx]


def get_filter_df_by_curies_index(
    df: DataframeOrSeries,
    *,
    column: str | int | None = None,
    curies: str | Collection[str],
) -> pd.Series[bool]:
    """Get an index of CURIEs in the given column that are the given CURIE(s)."""
    series = _get_series(df, column)
    if isinstance(curies, str):
        return series == curies
    else:
        return series.isin(set(curies))


def get_df_curies_index(
    df: DataframeOrSeries, *, column: str | int | None = None
) -> dict[str, list[int]]:
    """Get a dictionary from CURIEs that appear in the column to the row indexes where they appear."""
    dd: defaultdict[str, list[int]] = defaultdict(list)
    for i, curie in enumerate(_get_series(df, column)):
        dd[curie].append(i)
    return dict(dd)


def filter_df_by_curies(
    df: pd.DataFrame,
    *,
    column: str | int,
    curies: str | Collection[str],
) -> pd.DataFrame:
    """Filter a dataframe based on CURIEs in a given column having a given prefix or set of prefixes.

    :param df: A dataframe
    :param column: The integer index or column name of a column containing CURIEs
    :param curies: The CURIE (given as a string) or collection of CURIEs (given as a
        list, set, etc.) to keep

    :returns: If not in place, return a new dataframe.
    """
    idx = get_filter_df_by_curies_index(df=df, column=column, curies=curies)
    return df[idx]


def get_df_prefixes_index(
    df: DataframeOrSeries,
    *,
    column: str | int | None = None,
    converter: Converter | None = None,
    validate: bool = False,
) -> dict[str, list[int]]:
    """Get a dictionary from prefixes that appear in the column to the row indexes where they appear."""
    dd: defaultdict[str, list[int]] = defaultdict(list)
    f = _get_curie_parser(converter=converter, validate=validate)
    for i, prefix in enumerate(_get_series(df, column).map(f)):
        dd[prefix].append(i)
    return dict(dd)


def get_df_unique_prefixes(
    df: DataframeOrSeries,
    *,
    column: str | int | None = None,
    converter: Converter | None = None,
    validate: bool = False,
) -> set[str]:
    """Get unique prefixes."""
    series = _get_series(df, column)
    f = _get_curie_parser(converter=converter, validate=validate)
    return set(series.map(f).unique())


def _get_series(df: DataframeOrSeries, column: str | int | None = None) -> pd.Series[str]:
    import pandas as pd

    if isinstance(df, pd.Series):
        return df

    if column is None:
        raise ValueError

    return df[column]
