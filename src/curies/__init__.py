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
    load_extended_prefix_map,
    load_jsonld_context,
    load_prefix_map,
    load_shacl,
    upgrade_prefix_map,
    write_extended_prefix_map,
    write_jsonld_context,
    write_shacl,
    write_tsv,
)
from .discovery import discover, discover_from_rdf
from .reconciliation import remap_curie_prefixes, remap_uri_prefixes, rewire
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
    "remap_curie_prefixes",
    "remap_uri_prefixes",
    "rewire",
    "upgrade_prefix_map",
    "get_version",
    # i/o
    "load_prefix_map",
    "load_extended_prefix_map",
    "load_jsonld_context",
    "load_shacl",
    "write_extended_prefix_map",
    "write_jsonld_context",
    "write_shacl",
    "write_tsv",
    # sources
    "get_obo_converter",
    "get_prefixcommons_converter",
    "get_monarch_converter",
    "get_go_converter",
    "get_bioregistry_converter",
    # discovery
    "discover",
    "discover_from_rdf",
]
