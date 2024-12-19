"""Idiomatic conversion between URIs and compact URIs (CURIEs)."""

from .api import (
    Converter,
    DuplicatePrefixes,
    DuplicateURIPrefixes,
    DuplicateValueError,
    NamedReference,
    Prefix,
    PrefixMap,
    Record,
    Records,
    Reference,
    ReferenceTuple,
    W3CValidationError,
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
    "DuplicatePrefixes",
    "W3CValidationError",
    "DuplicateURIPrefixes",
    "DuplicateValueError",
    "NamedReference",
    "Prefix",
    "PrefixMap",
    "Record",
    "Records",
    "Reference",
    "ReferenceTuple",
    "chain",
    "discover",
    "discover_from_rdf",
    "get_bioregistry_converter",
    "get_go_converter",
    "get_monarch_converter",
    "get_obo_converter",
    "get_prefixcommons_converter",
    "get_version",
    "load_extended_prefix_map",
    "load_jsonld_context",
    "load_prefix_map",
    "load_shacl",
    "remap_curie_prefixes",
    "remap_uri_prefixes",
    "rewire",
    "upgrade_prefix_map",
    "write_extended_prefix_map",
    "write_jsonld_context",
    "write_shacl",
    "write_tsv",
]
