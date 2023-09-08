# -*- coding: utf-8 -*-

"""Idiomatic conversion between URIs and compact URIs (CURIEs)."""

from .api import (
    Converter,
    DuplicatePrefixes,
    DuplicateURIPrefixes,
    DuplicateValueError,
    Record,
    Reference,
    ReferenceTuple,
    chain,
    read_prefix_map,
    read_extended_prefix_map,
)
from .sources import (
    get_bioregistry_converter,
    get_go_converter,
    get_monarch_converter,
    get_obo_converter,
    get_prefixcommons_converter,
)
from .version import get_version

__all__ = [
    "Converter",
    "Record",
    "ReferenceTuple",
    "Reference",
    "DuplicateValueError",
    "DuplicateURIPrefixes",
    "DuplicatePrefixes",
    "chain",
    "get_version",
    # i/o
    "read_prefix_map",
    "read_extended_prefix_map",
    # sources
    "get_obo_converter",
    "get_prefixcommons_converter",
    "get_monarch_converter",
    "get_go_converter",
    "get_bioregistry_converter",
]
