"""A compatibility layer for pydantic 1 and 2."""

import warnings

from pydantic import __version__ as pydantic_version

__all__ = [
    "PYDANTIC_V1",
    "field_validator",
    "get_field_validator_values",
]

PYDANTIC_V1 = pydantic_version.startswith("1.")

if PYDANTIC_V1:
    from pydantic import validator as field_validator

    warnings.warn(
        "The `curies` package will drop Pydantic V1 support on "
        "October 31st, 2024, coincident with the obsolescence of Python 3.8 "
        "(see https://endoflife.date/python). This will "
        "happen with the v0.8.0 release of the `curies` package.",
        DeprecationWarning,
        stacklevel=1,
    )
else:
    from pydantic import field_validator


def get_field_validator_values(values, key: str):  # type:ignore
    """Get the value for the key from a field validator object, cross-compatible with Pydantic 1 and 2."""
    if PYDANTIC_V1:
        return values[key]
    else:
        return values.data[key]
