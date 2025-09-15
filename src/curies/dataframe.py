"""Dataframe operations."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Collection
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, TypeGuard, Union, cast

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
    validate: bool = False,
    converter: Converter | None = None,
) -> pd.Series[bool]:
    """Get an index of CURIEs in the given column that start with the prefix(es).

    :param df: A dataframe or series. If a dataframe is given, the ``column`` must not be none.
    :param column: The column to check, if a dataframe was passed. If a series was passed, this can be left as none.
    :param prefixes: The prefix or set of prefixes to identify
    :param method: The indexing method
    :param validate: Should the prefixes be validated against the converter?
    :param converter: A converter for validating CURIEs

    :returns: A pandas boolean series that corresponds to the rows of the dataframe or series provided

    :raises ValueError: If validation is set to true but no converter is passed

    Example usage:

    .. code-block:: python

        import pandas as pd
        from curies.dataframe import get_filter_df_by_prefixes_index

        rows = [
            ("DOID:0080795", "skos:exactMatch", "EFO:0003029", "semapv:ManualMappingCuration"),
            ("DOID:0080795", "skos:exactMatch", "mesh:D015471", "semapv:ManualMappingCuration"),
            ("DOID:0080799", "skos:exactMatch", "EFO:1000527", "semapv:ManualMappingCuration"),
            ("DOID:0080808", "skos:exactMatch", "mesh:D000069295", "semapv:ManualMappingCuration"),
        ]
        df = pd.DataFrame(
            rows, columns=["subject_id", "predicate_id", "object_id", "mapping_justification"]
        )
        idx = get_filter_df_by_prefixes_index(df, column="object_id", prefixes=["EFO"])
        filtered_df = df[idx]
    """
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
    validate: bool = False,
    converter: Converter | None = None,
) -> pd.DataFrame:
    """Filter a dataframe based on CURIEs in a given column having a given prefix or set of prefixes.

    :param df: A dataframe
    :param column: The integer index or column name of a column containing CURIEs
    :param prefixes: The prefix (given as a string) or collection of prefixes (given as a
        list, set, etc.) to keep
    :param method: The implementation for getting the prefix index
    :param validate: Should the prefixes be validated against the converter?
    :param converter: A converter for validating CURIEs

    :returns: If not in place, return a new dataframe.

    Example usage:

    .. code-block:: python

        import pandas as pd
        from curies.dataframe import filter_df_by_prefixes

        rows = [
            ("DOID:0080795", "skos:exactMatch", "EFO:0003029", "semapv:ManualMappingCuration"),
            ("DOID:0080795", "skos:exactMatch", "mesh:D015471", "semapv:ManualMappingCuration"),
            ("DOID:0080799", "skos:exactMatch", "EFO:1000527", "semapv:ManualMappingCuration"),
            ("DOID:0080808", "skos:exactMatch", "mesh:D000069295", "semapv:ManualMappingCuration"),
        ]
        df = pd.DataFrame(
            rows, columns=["subject_id", "predicate_id", "object_id", "mapping_justification"]
        )
        filtered_df = filter_df_by_prefixes(df, column="object_id", prefixes=["EFO"])

    This results in the following dataframe:

    ============ =============== =========== ============================
    subject_id   predicate_id    object_id   mapping_justification
    ============ =============== =========== ============================
    DOID:0080795 skos:exactMatch EFO:0003029 semapv:ManualMappingCuration
    DOID:0080799 skos:exactMatch EFO:1000527 semapv:ManualMappingCuration
    ============ =============== =========== ============================

    Internally, this function uses :func:`get_filter_df_by_prefixes_index`.
    """
    idx = get_filter_df_by_prefixes_index(
        df=df,
        column=column,
        prefixes=prefixes,
        method=method,
        converter=converter,
        validate=validate,
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

    Example usage:

    .. code-block:: python

        import pandas as pd
        from curies.dataframe import filter_df_by_curies

        rows = [
            ("DOID:0080795", "skos:exactMatch", "EFO:0003029", "semapv:ManualMappingCuration"),
            ("DOID:0080795", "skos:exactMatch", "mesh:D015471", "semapv:ManualMappingCuration"),
            ("DOID:0080799", "skos:exactMatch", "EFO:1000527", "semapv:ManualMappingCuration"),
            ("DOID:0080808", "skos:exactMatch", "mesh:D000069295", "semapv:ManualMappingCuration"),
        ]
        df = pd.DataFrame(
            rows, columns=["subject_id", "predicate_id", "object_id", "mapping_justification"]
        )
        filtered_df = filter_df_by_curies(df, column="subject_id", prefixes=["DOID:0080795"])

    This results in the following dataframe:

    ============ =============== ============ ============================
    subject_id   predicate_id    object_id    mapping_justification
    ============ =============== ============ ============================
    DOID:0080795 skos:exactMatch EFO:0003029  semapv:ManualMappingCuration
    DOID:0080795 skos:exactMatch mesh:D015471 semapv:ManualMappingCuration
    ============ =============== ============ ============================
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
    validate: bool = False,
    converter: Converter | None = None,
) -> set[str]:
    """Get unique prefixes.

    :param df: A dataframe or series. If a dataframe is given, the ``column`` must not be none.
    :param column: The column to check, if a dataframe was passed. If a series was passed, this can be left as none.
    :param validate: Should the prefixes be validated against the converter?
    :param converter: A converter for validating CURIEs

    :returns: A set of prefixes appearing in CURIEs in the given column

    .. code-block:: python

        import pandas as pd
        from curies.dataframe import get_df_unique_prefixes

        rows = [
            ("DOID:0080795", "skos:exactMatch", "EFO:0003029", "semapv:ManualMappingCuration"),
            ("DOID:0080795", "skos:exactMatch", "mesh:D015471", "semapv:ManualMappingCuration"),
            ("DOID:0080799", "skos:exactMatch", "EFO:1000527", "semapv:ManualMappingCuration"),
            ("DOID:0080808", "skos:exactMatch", "mesh:D000069295", "semapv:ManualMappingCuration"),
        ]
        df = pd.DataFrame(
            rows, columns=["subject_id", "predicate_id", "object_id", "mapping_justification"]
        )
        assert get_df_unique_prefixes(df, column="object_id") == {"EFO", "mesh"}
    """
    series = _get_series(df, column)
    f = _get_curie_parser(converter=converter, validate=validate)
    return set(series.map(f).unique())


def _disallowed_dtype(series: pd.Series[Any] | str) -> TypeGuard[pd.Series[str]]:
    import numpy as np

    if isinstance(series, str):
        return False

    return series.dtype != np.str_ and series.dtype != np.dtype("O")


def _get_series(df_or_series: DataframeOrSeries, column: str | int | None = None) -> pd.Series[str]:
    import pandas as pd

    if isinstance(df_or_series, pd.Series):
        if _disallowed_dtype(df_or_series):
            raise TypeError(
                f"passed series that does not have strings: {df_or_series.dtype=} {type(df_or_series.dtype)=}\n\n{df_or_series}"
            )
        return df_or_series

    if column is None:
        raise ValueError("must pass non-none column when using a dataframe directly")

    series = df_or_series[column]
    if _disallowed_dtype(series):
        raise TypeError(
            f"passed series that does not have strings: {series.dtype=} {type(series.dtype)=}\n\n{series}"
        )
    return cast("pd.Series[str]", series)
