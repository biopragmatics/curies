# -*- coding: utf-8 -*-

"""Idiomatic conversion between URIs and compact URIs (CURIEs)."""

from .api import Converter, DuplicatePrefixes, DuplicateURIPrefixes, Record, chain
from .sources import (
    get_bioregistry_converter,
    get_go_converter,
    get_monarch_converter,
    get_obo_converter,
    get_prefixcommons_converter,
)
from .version import get_version
from .web import get_blueprint

__all__ = [
    "Converter",
    "Record",
    "DuplicateURIPrefixes",
    "DuplicatePrefixes",
    "chain",
    "get_version",
    "get_obo_converter",
    "get_prefixcommons_converter",
    "get_monarch_converter",
    "get_go_converter",
    "get_bioregistry_converter",
    "get_blueprint",
]
