# -*- coding: utf-8 -*-

"""Idiomatic conversion between URIs and compact URIs (CURIEs)."""

from .api import Converter
from .version import get_version

__all__ = [
    "Converter",
    "get_version",
]
