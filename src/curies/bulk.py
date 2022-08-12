"""Bulk processing utilities."""

from typing import TYPE_CHECKING, Any, Iterable, Sequence, Tuple, TypeVar

from .api import Converter

if TYPE_CHECKING:
    import pandas

__all__ = [
    # Pandas dataframe utilities
    "df_curies_to_uris",
    "df_uris_to_curies",
    # Stream utilities
    "stream_curies_to_uris",
    "stream_uris_to_curies",
]

X = TypeVar("X")


def df_uris_to_curies(converter: Converter, df: "pandas.DataFrame", column: str) -> None:
    """Convert all URIs in the given column to CURIEs.

    :param converter: A converter
    :param df: A pandas DataFrame
    :param column: The column in the dataframe containing URIs to convert to CURIEs.
    """
    df[column] = df[column].map(converter.compress)


def df_curies_to_uris(converter: Converter, df: "pandas.DataFrame", column: str) -> None:
    """Convert all CURIEs in the given column to URIs.

    :param converter: A converter
    :param df: A pandas DataFrame
    :param column: The column in the dataframe containing CURIEs to convert to URIs.
    """
    df[column] = df[column].map(converter.expand)


def stream_uris_to_curies(
    converter: Converter, records: Iterable[Sequence[Any]], idx: int
) -> Iterable[Tuple[Any, ...]]:
    """Convert all URIs in the given position (either index or key) to CURIEs."""
    for record in records:
        yield *record[:idx], converter.compress(record[idx]), *record[idx + 1 :]


def stream_curies_to_uris(
    converter: Converter, records: Iterable[Sequence[Any]], idx: int
) -> Iterable[Tuple[Any, ...]]:
    """Convert all CURIEs in the given position (either index or key) to URIs."""
    for record in records:
        yield *record[:idx], converter.expand(record[idx]), *record[idx + 1 :]
