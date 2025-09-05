"""Dataframe operations."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection
from typing import TYPE_CHECKING, Callable, Literal

from typing_extensions import TypeAlias

from .utils import _prefix_from_curie

if TYPE_CHECKING:
    import pandas as pd

    from .api import Converter

__all__ = [
    "PrefixIndexMethod",
    "get_df_curies_index",
    "get_df_keep_curies_index",
    "get_df_keep_prefixes_index",
    "get_df_prefixes_index",
    "keep_df_curies",
    "keep_df_prefixes",
]


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
    df: pd.DataFrame, column: int | str, converter: Converter, validate: bool
) -> pd.Series:
    return df[column].map(_get_curie_parser(converter=converter, validate=validate))


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


def get_df_keep_prefixes_index(
    df: pd.DataFrame,
    column: str | int,
    prefix: str | Collection[str],
    *,
    method: PrefixIndexMethod | None = None,
    converter: Converter | None = None,
    validate: bool = False,
) -> pd.Series:
    """Get an index of CURIEs in the given column that start with the prefix(es)."""
    if method == "iterative" or method is None:
        return df[column].map(_get_prefix_checker(prefix))
    elif method == "precalculated":
        if converter is None:  # pragma: no cover
            raise ValueError("a converter is required for method B")
        prefix_series = _get_prefixes_from_curie_column(df, column, converter, validate=validate)
        if isinstance(prefix, str):
            return prefix_series == prefix
        else:
            return prefix_series.isin(prefix)
    else:  # pragma: no cover
        raise ValueError(f"invalid method given: {method}")


def keep_df_prefixes(
    df: pd.DataFrame,
    column: str | int,
    prefix: str | Collection[str],
    *,
    method: PrefixIndexMethod | None = None,
    converter: Converter | None = None,
) -> pd.DataFrame:
    """Filter a dataframe based on CURIEs in a given column having a given prefix or set of prefixes.

    :param df: A dataframe
    :param column:
        The integer index or column name of a column containing CURIEs
    :param prefix:
        The prefix (given as a string) or collection of prefixes (given as a list, set, etc.) to keep
    :param method: The implementation for getting the prefix index
    :param converter: A converter
    :returns: If not in place, return a new dataframe.
    """
    idx = get_df_keep_prefixes_index(
        df=df, column=column, prefix=prefix, method=method, converter=converter
    )
    return df[idx]


def get_df_keep_curies_index(
    df: pd.DataFrame,
    column: str | int,
    curie: str | Collection[str],
) -> pd.Series:
    """Get an index of CURIEs in the given column that are the given CURIE(s)."""
    if isinstance(curie, str):
        return df[column] == curie
    else:
        return df[column].isin(set(curie))


def get_df_curies_index(df: pd.DataFrame, column: str | int) -> dict[str, list[int]]:
    """Get a dictionary from CURIEs that appear in the column to the row indexes where they appear."""
    dd: defaultdict[str, list[int]] = defaultdict(list)
    for i, curie in enumerate(df[column]):
        dd[curie].append(i)
    return dict(dd)


def keep_df_curies(
    df: pd.DataFrame,
    column: str | int,
    curie: str | Collection[str],
) -> pd.DataFrame:
    """Filter a dataframe based on CURIEs in a given column having a given prefix or set of prefixes.

    :param df: A dataframe
    :param column:
        The integer index or column name of a column containing CURIEs
    :param curie:
        The CURIE (given as a string) or collection of CURIEs (given as a list, set, etc.) to keep
    :returns: If not in place, return a new dataframe.
    """
    idx = get_df_keep_curies_index(df=df, column=column, curie=curie)
    return df[idx]


def get_df_prefixes_index(
    df: pd.DataFrame,
    column: str | int,
    *,
    converter: Converter | None = None,
    validate: bool = False,
) -> dict[str, list[int]]:
    """Get a dictionary from prefixes that appear in the column to the row indexes where they appear."""
    dd: defaultdict[str, list[int]] = defaultdict(list)
    f = _get_curie_parser(converter=converter, validate=validate)
    for i, prefix in enumerate(df[column].map(f)):
        dd[prefix].append(i)
    return dict(dd)
