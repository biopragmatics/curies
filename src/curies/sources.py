# -*- coding: utf-8 -*-

"""External sources of contexts."""

from typing import Any, Optional

import requests

from .api import Converter, Record

__all__ = [
    "get_obo_converter",
    "get_prefixcommons_converter",
    "get_monarch_converter",
    "get_go_converter",
    "get_bioregistry_converter",
]

BIOREGISTRY_CONTEXTS = (
    "https://raw.githubusercontent.com/biopragmatics/bioregistry/main/exports/contexts"
)


def get_obo_converter() -> Converter:
    """Get the latest OBO Foundry context."""
    # See configuration on https://github.com/OBOFoundry/purl.obolibrary.org/blob/master/www/.htaccess
    # to see where this PURL points
    url = "http://purl.obolibrary.org/meta/obo_context.jsonld"
    return Converter.from_jsonld(url)


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
    return Converter.from_jsonld(url)


def get_monarch_converter() -> Converter:
    """Get the Prefix Commons-maintained Monarch context."""
    return get_prefixcommons_converter("monarch_context")


def get_go_converter() -> Converter:
    """Get the Prefix Commons-maintained GO context."""
    return get_prefixcommons_converter("go_context")


def get_bioregistry_converter(web: bool = False, **kwargs: Any) -> Converter:
    """Get the latest Bioregistry context."""
    if not web:
        try:
            import bioregistry
        except ImportError:  # pragma: no cover
            pass
        else:
            return Converter.from_extended_prefix_map(bioregistry.manager.get_curies_records())
    url = f"{BIOREGISTRY_CONTEXTS}/bioregistry.epm.json"
    return Converter.from_extended_prefix_map(url, **kwargs)


MIRIAM_URL = "https://registry.api.identifiers.org/resolutionApi/getResolverDataset"


def get_miriam_converter() -> Converter:
    """Get a prefix map from MIRIAM."""
    res_json = requests.get(MIRIAM_URL).json()
    records = []
    for record in res_json["payload"]["namespaces"]:
        prefix = record["prefix"]
        uri_prefix: Optional[str] = None
        uri_prefix_synonyms = []
        for resource in record.get("resources", []):
            if resource.get("deprecated"):
                continue
            pattern = resource["urlPattern"]
            if pattern.count("{$id}") != 1 or not pattern.endswith("{$id}"):
                continue
            pattern = pattern[: -len("{$id}")]
            if resource["official"] and uri_prefix is None:
                uri_prefix = pattern
            else:
                uri_prefix_synonyms.append(pattern)
        if not uri_prefix:
            continue
        records.append(
            Record(prefix=prefix, uri_prefix=uri_prefix, uri_prefix_synonyms=uri_prefix_synonyms)
        )

    # FIXME Identifiers.org has duplicate URI prefixes for kegg and several other groups
    return Converter(records)
