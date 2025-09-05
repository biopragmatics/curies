"""Utilities for working with strings."""

from __future__ import annotations

__all__ = [
    "NoCURIEDelimiterError",
    "_split",
]


class NoCURIEDelimiterError(ValueError):
    """An error thrown on a string with no delimiter."""

    def __init__(self, curie: str):
        """Initialize the error."""
        self.curie = curie

    def __str__(self) -> str:
        return f"{self.curie} does not appear to be a CURIE - missing a delimiter"


def _split(curie: str, *, sep: str = ":") -> tuple[str, str]:
    """Split a CURIE string using string operations."""
    prefix, delimiter, identifier = curie.partition(sep)
    if not delimiter:
        raise NoCURIEDelimiterError(curie)
    return prefix, identifier


def _prefix_from_curie(curie: str, *, sep: str = ":") -> str:
    """Split a CURIE string using string operations and return the prefix."""
    return _split(curie, sep=sep)[0]
