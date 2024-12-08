"""Version information for :mod:`curies`."""

__all__ = [
    "VERSION",
    "get_version",
]

VERSION = "0.9.2-dev"


def get_version() -> str:
    """Get the :mod:`curies` version string."""
    return VERSION
