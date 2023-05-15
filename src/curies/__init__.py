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
)
from .sources import (
    get_bioregistry_converter,
    get_go_converter,
    get_monarch_converter,
    get_obo_converter,
    get_prefixcommons_converter,
)
from .version import get_version
from .web import get_fastapi_app, get_fastapi_router, get_flask_app, get_flask_blueprint

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
    # sources
    "get_obo_converter",
    "get_prefixcommons_converter",
    "get_monarch_converter",
    "get_go_converter",
    "get_bioregistry_converter",
    # Web extras
    "get_flask_blueprint",
    "get_flask_app",
    "get_fastapi_router",
    "get_fastapi_app",
]
