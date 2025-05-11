"""Version information for :mod:`curies`."""

__all__ = [
    "VERSION",
    "get_version",
]

VERSION = "0.10.19-dev"


def get_version() -> str:
    """Get the :mod:`curies` version string."""
    return VERSION
