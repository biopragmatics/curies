"""Utilities for SSSOM."""

from __future__ import annotations

import itertools as itt
from collections.abc import Collection, Iterable
from typing import TYPE_CHECKING, Literal, TypeAlias

import pandas as pd

from curies.dataframe import (
    get_df_curies_index,
    get_df_prefixes_index,
    get_keep_df_curies_index,
    get_keep_df_prefixes_index,
)

if TYPE_CHECKING:
    import sssom

__all__ = [
    "split_dataframe_by_prefix",
    "split_msdf_by_prefix",
]


def split_msdf_by_prefix(
    msdf: sssom.MappingSetDataFrame,
    subject_prefixes: Collection[str],
    predicates: Collection[str],
    object_prefixes: Collection[str],
) -> dict[str, sssom.MappingSetDataFrame]:
    """Split a MSDF, a drop-in replacement for :func:`sssom.parsers.split_dataframe_by_prefix`."""
    from sssom.io import from_sssom_dataframe

    rr = split_dataframe_by_prefix(msdf.df, subject_prefixes, predicates, object_prefixes)
    rv = {}
    for (subject_prefix, predicate, object_prefix), df in rr:
        predicate_reference = msdf.converter.parse_curie(predicate, strict=True)
        subconverter = msdf.converter.get_subconverter(
            [subject_prefix, predicate_reference.prefix, object_prefix]
        )
        split = f"{subject_prefix.lower()}_{predicate.lower()}_{object_prefix.lower()}"
        rv[split] = from_sssom_dataframe(df, prefix_map=dict(subconverter.bimap), meta=msdf.meta)
    return rv


SplitMethod: TypeAlias = Literal["disjoint-indexes", "dense-indexes"]


def split_dataframe_by_prefix(
    df: pd.DataFrame,
    subject_prefixes: str | Collection[str],
    predicates: str | Collection[str],
    object_prefixes: str | Collection[str],
    *,
    method: SplitMethod | None = None,
) -> Iterable[tuple[tuple[str, str, str], pd.DataFrame]]:
    """Iterate over splits on a dataframe."""
    if isinstance(subject_prefixes, str):
        subject_prefixes = [subject_prefixes]
    if isinstance(predicates, str):
        predicates = [predicates]
    if isinstance(object_prefixes, str):
        object_prefixes = [object_prefixes]

    if method == "disjoint-indexes" or method is None:
        s_indexes = {
            subject_prefix: get_keep_df_prefixes_index(
                df, column="subject_id", prefix=subject_prefix
            )
            for subject_prefix in subject_prefixes
        }
        p_indexes = {
            predicate: get_keep_df_curies_index(df, column="predicate_id", curie=predicate)
            for predicate in predicates
        }
        o_indexes = {
            object_prefix: get_keep_df_prefixes_index(df, column="object_id", prefix=object_prefix)
            for object_prefix in object_prefixes
        }
        for subject_prefix, predicate, object_prefix in itt.product(
            subject_prefixes, predicates, object_prefixes
        ):
            idx = s_indexes[subject_prefix] & p_indexes[predicate] & o_indexes[object_prefix]
            if not idx.any():
                continue
            yield (subject_prefix, predicate, object_prefix), df[idx]

    elif method == "dense-indexes":
        s_index = get_df_prefixes_index(df, "subject_id")
        p_index = get_df_curies_index(df, "predicate_id")
        o_index = get_df_prefixes_index(df, "object_id")
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
