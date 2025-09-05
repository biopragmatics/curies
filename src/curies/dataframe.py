"""Dataframe operations."""

from __future__ import annotations

import itertools as itt
from collections.abc import Collection, Iterable
from typing import TYPE_CHECKING, Callable, Literal, TypeAlias

from curies.api import Converter, _split

if TYPE_CHECKING:
    import pandas as pd
    import sssom

__all__ = [
    "filter_df_prefix",
    "get_prefix_index",
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
    df: pd.DataFrame, column: int | str, converter: Converter, validate: bool = True
) -> pd.Series:
    # TODO what if it can't parse?
    # TODO handle None?
    # TODO handle invalid CURIEs?

    if validate:
        return df[column].map(lambda curie: converter.parse_curie(curie, strict=True).prefix)
    else:
        return df[column].map(lambda curie: _split(curie)[0])


Method: TypeAlias = Literal["a", "b"]


def get_prefix_index(
    df: pd.DataFrame,
    column: str | int,
    prefix: str | Collection[str],
    *,
    method: Method | None = None,
    converter: Converter | None = None,
) -> pd.Series:
    """Get an index of CURIEs in the given column that start with the prefix(es)."""
    if method == "a":
        return df[column].map(_get_prefix_checker(prefix))
    elif method == "b":
        if converter is None:
            raise ValueError("a converter is required for method B")
        prefix_series = _get_prefixes_from_curie_column(df, column, converter)
        if isinstance(prefix, str):
            return prefix_series == prefix
        else:
            return prefix_series.isin(prefix)
    else:
        raise ValueError


def filter_df_prefix(
    df: pd.DataFrame,
    column: str | int,
    prefix: str,
    *,
    method: Method | None = None,
    converter: Converter | None = None,
) -> pd.DataFrame:
    """Filter a dataframe based on CURIEs in a given column having a given prefix or set of prefixes.

    :param df: A dataframe
    :param column:
        The integer index or column name of a column containing CURIEs
    :param prefix:
        The prefix (given as a string) or collection of prefixes (given as a list, set, etc.) to keep
    :returns: If not in place, return a new dataframe.
    """
    idx = get_prefix_index(df=df, column=column, prefix=prefix, method=method, converter=converter)
    return df[idx]


def split_msdf_by_prefix(
    msdf: sssom.MappingSetDataFrame,
    subject_prefixes: Collection[str],
    predicates: Collection[str],
    object_prefixes: Collection[str],
) -> dict[str, sssom.MappingSetDataFrame]:
    """Split a MSDF, a drop-in replacement for :func:`sssom.parsers.split_dataframe_by_prefix`."""
    from sssom.io import from_sssom_dataframe

    rr = _split_dataframe_by_prefix(msdf.df, subject_prefixes, predicates, object_prefixes)
    rv = {}
    for (subject_prefix, predicate, object_prefix), df in rr:
        predicate_reference = msdf.converter.parse_curie(predicate, strict=True)
        subconverter = msdf.converter.get_subconverter(
            [subject_prefix, predicate_reference.prefix, object_prefix]
        )
        split = f"{subject_prefix.lower()}_{predicate.lower()}_{object_prefix.lower()}"
        rv[split] = from_sssom_dataframe(df, prefix_map=dict(subconverter.bimap), meta=msdf.meta)
    return rv


# this is split out from SSSOM
def _split_dataframe_by_prefix(
    df: pd.DataFrame,
    subject_prefixes: Collection[str],
    predicates: Collection[str],
    object_prefixes: Collection[str],
) -> Iterable[tuple[tuple[str, str, str], pd.DataFrame]]:
    s_indexes = {
        subject_prefix: get_prefix_index(df, column="subject_id", prefix=subject_prefix)
        for subject_prefix in subject_prefixes
    }
    p_indexes = {predicate: df["predicate_id"] == predicate for predicate in predicates}
    o_indexes = {
        object_prefix: get_prefix_index(df, column="object_id", prefix=object_prefix)
        for object_prefix in object_prefixes
    }
    for subject_prefix, predicate, object_prefix in itt.product(
        subject_prefixes, predicates, object_prefixes
    ):
        idx = s_indexes[subject_prefix] & p_indexes[predicate] & o_indexes[object_prefix]
        if not idx.any():
            continue
        yield (subject_prefix, predicate, object_prefix), df[idx]
