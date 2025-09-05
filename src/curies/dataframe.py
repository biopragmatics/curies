"""Dataframe operations."""

from __future__ import annotations

import itertools as itt
from collections import defaultdict
from collections.abc import Collection, Iterable
from typing import TYPE_CHECKING, Callable, Literal, TypeAlias

from curies.api import Converter, _split

if TYPE_CHECKING:
    import pandas as pd
    import sssom

__all__ = [
    "filter_df_curie",
    "filter_df_prefix",
    "get_curie_index",
    "get_dense_curie",
    "get_dense_prefix",
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
    return df[column].map(_get_parse_curie(converter=converter, validate=validate))


def _get_parse_curie(
    *, converter: Converter | None = None, validate: bool = False
) -> Callable[[str], str]:
    # TODO what if it can't parse?
    # TODO handle None?
    # TODO handle invalid CURIEs?

    if not validate:

        def _func(curie: str) -> str:
            return _split(curie)[0]
    elif converter is None:
        raise ValueError("converter is required for validation")
    else:

        def _func(curie: str) -> str:
            reference = converter.parse_curie(curie, strict=True)
            return reference.prefix

    return _func


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
    if method == "a" or method is None:
        return df[column].map(_get_prefix_checker(prefix))
    elif method == "b":
        if converter is None:  # pragma: no cover
            raise ValueError("a converter is required for method B")
        prefix_series = _get_prefixes_from_curie_column(df, column, converter)
        if isinstance(prefix, str):
            return prefix_series == prefix
        else:
            return prefix_series.isin(prefix)
    else:  # pragma: no cover
        raise ValueError(f"invalid method given: {method}")


def filter_df_prefix(
    df: pd.DataFrame,
    column: str | int,
    prefix: str | Collection[str],
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


def get_curie_index(
    df: pd.DataFrame,
    column: str | int,
    curie: str | Collection[str],
) -> pd.Series:
    """Get an index of CURIEs in the given column that are the given CURIE(s)."""
    if isinstance(curie, str):
        return df[column] == curie
    else:
        return df[column].isin(set(curie))


def filter_df_curie(
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
    idx = get_curie_index(df=df, column=column, curie=curie)
    return df[idx]


def get_dense_prefix(
    df: pd.DataFrame,
    column: str | int,
    *,
    converter: Converter | None = None,
    validate: bool = False,
) -> dict[str, list[int]]:
    """Get a dictionary from prefixes that appear in the column to the row indexes where they appear."""
    dd: defaultdict[str, list[int]] = defaultdict(list)
    f = _get_parse_curie(converter=converter, validate=validate)
    for i, prefix in enumerate(df[column].map(f)):
        dd[prefix].append(i)
    return dict(dd)


def get_dense_curie(df: pd.DataFrame, column: str | int) -> dict[str, list[int]]:
    """Get a dictionary from CURIEs that appear in the column to the row indexes where they appear."""
    dd: defaultdict[str, list[int]] = defaultdict(list)
    for i, curie in enumerate(df[column]):
        dd[curie].append(i)
    return dict(dd)


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
    *,
    method: Literal[1, 2] = 1,
) -> Iterable[tuple[tuple[str, str, str], pd.DataFrame]]:
    if method == 1:
        s_indexes = {
            subject_prefix: get_prefix_index(df, column="subject_id", prefix=subject_prefix)
            for subject_prefix in subject_prefixes
        }
        p_indexes = {
            predicate: get_curie_index(df, column="predicate_id", curie=predicate)
            for predicate in predicates
        }
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

    elif method == 2:
        s_index = get_dense_prefix(df, "subject_id")
        p_index = get_dense_curie(df, "predicate_id")
        o_index = get_dense_prefix(df, "object_id")
        for subject_prefix, predicate, object_prefix in itt.product(
            subject_prefixes, predicates, object_prefixes
        ):
            method_2_idx: list[int] = sorted(
                set(s_index.get(subject_prefix, []))
                .intersection(p_index.get(predicate, []))
                .intersection(o_index.get(object_prefix, []))
            )
            if not method_2_idx:
                continue
            yield (subject_prefix, predicate, object_prefix), df.iloc[method_2_idx]

    else:
        raise ValueError
