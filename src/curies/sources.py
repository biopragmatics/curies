# -*- coding: utf-8 -*-

"""External sources of contexts."""

from typing import Any

from .api import Converter

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
    """Get the latest OBO Foundry context.

    :returns:
        A converter object representing the OBO Foundry's JSON-LD context,
        which contains a simple mapping from OBO Foundry preferred prefixes
        for ontologies that contain case stylization (e.g., ``GO``, not ``go``; ``VariO``, not ``vario``).

        It does not include synonyms nor any non-ontology prefixes - e.g., it does not include
        semantic web prefixes like ``rdfs``, it does not include other useful biomedical prefixes
        like ``hgnc``.

    If you want a more comprehensive prefix map, consider using the Bioregistry
    via :func:`get_bioregistry_converter` or by chaining the OBO converter in front of the
    Bioregistry depending on your personal/project preferences using :func:`curies.chain`.

    Provenance:

    - This JSON-LD context is generated programmatically
      by https://github.com/OBOFoundry/OBOFoundry.github.io/blob/master/util/processor.py.
    - The file is accessed via from http://purl.obolibrary.org/meta/obo_context.jsonld,
      which is configured through the OBO Foundry's PURL server with
      https://github.com/OBOFoundry/purl.obolibrary.org/blob/master/www/.htaccess
      and ultimately points to
      https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/obo_context.jsonl
    """
    # See configuration on
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
            epm = bioregistry.manager.get_curies_records()  # pragma: no cover
            return Converter.from_extended_prefix_map(epm)  # pragma: no cover
    url = f"{BIOREGISTRY_CONTEXTS}/bioregistry.epm.json"
    return Converter.from_extended_prefix_map(url, **kwargs)
