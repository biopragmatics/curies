# -*- coding: utf-8 -*-

"""Idiomatic conversion between URIs and compact URIs (CURIEs)."""

from .api import Converter, chain
from .bulk import df_curies_to_uris, df_uris_to_curies, stream_curies_to_uris, stream_uris_to_curies
from .sources import (
    get_bioregistry_converter,
    get_go_converter,
    get_go_obo_converter,
    get_monarch_converter,
    get_obo_converter,
    get_prefixcommons_converter,
)
from .version import get_version

__all__ = [
    "Converter",
    "chain",
    "get_version",
    "get_obo_converter",
    "get_prefixcommons_converter",
    "get_monarch_converter",
    "get_go_converter",
    "get_bioregistry_converter",
    "get_go_obo_converter",
    # Bulk utilities
    "df_curies_to_uris",
    "df_uris_to_curies",
    "stream_curies_to_uris",
    "stream_uris_to_curies",
]
