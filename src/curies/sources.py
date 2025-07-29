"""External sources of contexts."""

from __future__ import annotations

from typing import Any

from .api import Converter

__all__ = [
    "get_bioregistry_converter",
    "get_go_converter",
    "get_monarch_converter",
    "get_obo_converter",
    "get_prefixcommons_converter",
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


def get_prefixcommons_converter(name: str = "monarch_context") -> Converter:
    """Get a Prefix Commons-maintained context.

    :param name: The name of the JSON-LD file (e.g., defaults to ``monarch_context``).
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
    """Get the latest extended prefix map from the Bioregistry [hoyt2022]_.

    :param web: If false, tries to import :mod:`bioregistry` and use
        :func:`bioregistry.get_converter` to get the converter. Otherwise,
        falls back to using the GitHub-hosted EPM export.
    :param kwargs:
        Keyword arguments to pass to :meth`:curies.Converter.from_extended_prefix_map`
        when using web-based loading.
    :returns: A converter representing the Bioregistry, which includes
        a comprehensive collection of prefixes, prefix synonyms, and
        URI prefix synonyms.

    Short summary of the Bioregistry:

    1. It deduplicates and harmonizes dozens of different resources that
       curate partially overlapping and conflicting prefix maps
    2. It contains detailed CURIE prefix synonyms to support standardization
    3. It enforces the generation of a self-consistent extended prefix map

    The Bioregistry's primary prefixes are all standardized to be lowercase,
    have minimal punctuation, and be the most idiomatic possible. When this
    conflicts with your personal preferences/community preferences, you can
    chain another converter in front of the Bioregistry converter using
    :func:`curies.chain`.

    However, the Bioregistry itself presents a more
    sustainable way of documenting these deviations in a community-oriented way
    using its "context" configurations. See https://bioregistry.io/context/ for
    more information. One excellent example of a community context is for the
    OBO community (see https://bioregistry.io/context/obo), which prioritizes
    OBO capitalized prefixes and makes a few minor changes for backwards compatibility
    (e.g., renaming Orphanet).

    .. [hoyt2022] `Unifying the identification of biomedical entities with the
       Bioregistry <https://www.nature.com/articles/s41597-022-01807-3>`_
    """
    if not web:
        try:
            import bioregistry
        except ImportError:  # pragma: no cover
            pass
        else:
            return bioregistry.manager.get_converter()
    url = f"{BIOREGISTRY_CONTEXTS}/bioregistry.epm.json"
    return Converter.from_extended_prefix_map(url, **kwargs)
