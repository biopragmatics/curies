# -*- coding: utf-8 -*-

"""External sources of contexts."""

from .api import Converter

__all__ = [
    "get_obo_converter",
    "get_prefixcommons_converter",
    "get_monarch_converter",
    "get_go_converter",
    "get_bioregistry_converter",
    "get_go_obo_converter",
]


def get_obo_converter() -> Converter:
    """Get the latest OBO Foundry context."""
    url = "https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/obo_context.jsonld"
    return Converter.from_jsonld_url(url)


def get_prefixcommons_converter(name: str) -> Converter:
    """Get a Prefix Commons-maintained context.

    :param name: The name of the JSON-LD file (e.g., ``monarch_context``).
        See the full list at https://github.com/prefixcommons/prefixcommons-py/tree/master/prefixcommons/registry.
    :returns:
        A converter
    """
    url = (
        "https://raw.githubusercontent.com/prefixcommons/prefixcommons-py/master/"
        f"prefixcommons/registry/{name}.jsonld"
    )
    return Converter.from_jsonld_url(url)


def get_monarch_converter() -> Converter:
    """Get the Prefix Commons-maintained Monarch context."""
    return get_prefixcommons_converter("monarch_context")


def get_go_converter() -> Converter:
    """Get the Prefix Commons-maintained GO context."""
    return get_prefixcommons_converter("go_context")


def get_go_obo_converter() -> Converter:
    """Get the Prefix Commons-maintained GO/OBO context."""
    return get_prefixcommons_converter("go_obo_context")


def get_bioregistry_converter() -> Converter:
    """Get the latest Bioregistry context."""
    url = (
        "https://raw.githubusercontent.com/biopragmatics/bioregistry/main/"
        "exports/contexts/bioregistry.context.jsonld"
    )
    return Converter.from_jsonld_url(url)
