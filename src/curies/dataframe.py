"""Dataframe operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload, Literal, Callable, Collection, Iterable
import itertools as itt
from curies import Converter

if TYPE_CHECKING:
    import pandas as pd
    import sssom

__all__ = [
    "get_prefix_index",
    "filter_df_prefix",
]


def _get_prefix_checker(prefix: str | Collection[str]) -> Callable[[str], bool]:
    """Get a function that checks if a CURIE starts with a prefix."""
    if isinstance(prefix, str):
        pp = prefix + ":"

        def func(x: str) -> bool:
            return x.startswith(pp)

    else:
        strings = {p + ":" for p in prefix}

        def func(x: str) -> bool:
            return any(x.startswith(pp) for pp in strings)

    return func


def _get_prefixes_from_curie_column(df: pd.DataFrame, column: int | str, converter: Converter) -> pd.Series:
    raise NotImplementedError


def get_prefix_index(
    df: pd.DataFrame, column: str | int, prefix: str | Collection[str], *, method: Literal['a', 'b'] = 'a',
    converter: Converter | None = None,
) -> pd.Series:
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


@overload
def filter_df_prefix(df: pd.DataFrame, prefix: str, *, inplace: Literal[True] = ...) -> None: ...


@overload
def filter_df_prefix(df: pd.DataFrame, prefix: str, *, inplace: Literal[False] = ...) -> pd.DataFrame: ...


def filter_df_prefix(df: pd.DataFrame, prefix: str, *, inplace: bool = False) -> pd.DataFrame | None:
    """"""
    if inplace:
        return _filter_df_prefix_inplace(df, prefix)
    else:
        return _filter_df_prefix(df, prefix)


def _filter_df_prefix_inplace(df: pd.DataFrame, prefix: str) -> None:
    raise NotImplementedError


def _filter_df_prefix(df: pd.DataFrame, column: str | int, prefix: str) -> pd.DataFrame:
    pp = prefix + ":"
    idx = df[column].map(lambda value: value.startswith(pp))


# this is split out from SSSOM
def split_dataframe_by_prefix(
    df: pd.DataFrame,
    subject_prefixes: Collection[str],
    predicates: Collection[str],
    object_prefixes: Collection[str],
) -> dict[tuple[str, str, str], pd.DataFrame]:
    rv = {}
    s_indexes = {
        subject_prefix: get_prefix_index(df, column="subject_id", prefix=subject_prefix)
        for subject_prefix in subject_prefixes
    }
    p_indexes = {
        predicate: df["predicate_id"] == predicate
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
        rv[subject_prefix, predicate, object_prefix] = df[idx]

    return rv


def split_msdf_by_prefix(
    msdf: sssom.MappingSetDataFrame,
    subject_prefixes: Collection[str],
    predicates: Collection[str],
    object_prefixes: Collection[str],
) -> dict[str, sssom.MappingSetDataFrame]:
    from sssom.io import from_sssom_dataframe
    rr = split_dataframe_by_prefix(msdf.df, subject_prefixes, predicates, object_prefixes)
    rv = {}
    for (subject_prefix, predicate, object_prefix), df in rr.items():
        c = msdf.converter.parse_curie(predicate, strict=True)
        subconverter = msdf.converter.get_subconverter(
            [subject_prefix, c.prefix, object_prefix]
        )
        split = f"{subject_prefix.lower()}_{predicate.lower()}_{object_prefix.lower()}"
        rv[split] = from_sssom_dataframe(
            df, prefix_map=dict(subconverter.bimap), meta=msdf.meta
        )
    return rv
