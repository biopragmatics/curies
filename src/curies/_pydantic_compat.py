"""A compatibility layer for pydantic 1 and 2."""

import warnings

from pydantic import __version__ as pydantic_version
from pydantic import field_validator

__all__ = [
    "field_validator",
    "get_field_validator_values",
]


def get_field_validator_values(values, key: str):  # type:ignore
    """Get the value for the key from a field validator object, cross-compatible with Pydantic 1 and 2."""
    return values.data[key]
