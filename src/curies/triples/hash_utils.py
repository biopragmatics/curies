"""Triple hashing utilities."""

from __future__ import annotations

import hashlib

from .model import Triple
from ..api import Converter

__all__ = [
    "encode_delimited_uris",
    "hash_triple",
]


def hash_triple(converter: Converter, triple: Triple) -> str:
    """Encode a triple with URL-safe base64 encoding.

    :param converter: A converter
    :param triple: A triple of CURIE objects

    :returns: An encoded triple of URIs

    .. seealso::

        https://ts4nfdi.github.io/mapping-sameness-identifier/

    >>> converter = curies.load_prefix_map(
    ...     {
    ...         "mesh": "http://id.nlm.nih.gov/mesh/",
    ...         "skos": "http://www.w3.org/2004/02/skos/core#",
    ...         "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
    ...     }
    ... )
    >>> triple = Triple(subject="mesh:C000089", predicate="skos:exactMatch", object="CHEBI:28646")
    >>> hash_triple(converter, triple)
    '36a1f9244ea7641a90987c82f33c25c0c13712ee8f48207b2a0825f8a4e4e26a'
    """
    return encode_delimited_uris(triple.as_uri_triple(converter))


def encode_delimited_uris(uri_triple: tuple[str, str, str]) -> str:
    """Encode a subject-predicate-object triple.

    :param uri_triple: A triple of URIs represented as strings

    :returns: An encoded triple of URIs

    .. seealso::

        https://ts4nfdi.github.io/mapping-sameness-identifier/

    >>> encode_delimited_uris(
    ...     (
    ...         "http://id.nlm.nih.gov/mesh/C000089",
    ...         "http://www.w3.org/2004/02/skos/core#exactMatch",
    ...         "http://purl.obolibrary.org/obo/CHEBI_28646",
    ...     )
    ... )
    '36a1f9244ea7641a90987c82f33c25c0c13712ee8f48207b2a0825f8a4e4e26a'
    """
    delimited_uris = " ".join(uri_triple)
    digest = hashlib.sha256(delimited_uris.encode("utf-8")).hexdigest()
    return digest
