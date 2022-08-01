# -*- coding: utf-8 -*-

"""Unopinionated conversion between URIs and compact URIs."""

from .api import Converter
from .version import get_version

__all__ = [
    "Converter",
    "get_version",
]
