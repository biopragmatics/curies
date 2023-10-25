# -*- coding: utf-8 -*-

"""Version information for :mod:`curies`."""

__all__ = [
    "VERSION",
    "get_version",
]

VERSION = "0.6.7-dev"


def get_version() -> str:
    """Get the :mod:`curies` version string."""
    return VERSION
