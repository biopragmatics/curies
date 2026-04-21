"""Triple hashing utilities."""

from __future__ import annotations

import hashlib

from .model import Triple
from ..api import Converter

__all__ = [
    "encode_curie_triple",
    "encode_uri_triple",
    "hash_triple",
]


def hash_triple(converter: Converter, triple: Triple, *, negate: bool = False) -> str:
    """Encode a triple with URL-safe base64 encoding.

    :param converter: A converter
    :param triple: A triple of CURIE objects
    :param negate: If true, considers the triple as "negative" and postpends a ``~`` to
        the hash

    :returns: An encoded triple of URIs

    .. seealso::

        https://ts4nfdi.github.io/mapping-sameness-identifier/

    >>> import curies
    >>> from curies.triples import Triple
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
    >>> hash_triple(converter, triple, negate=True)
    '36a1f9244ea7641a90987c82f33c25c0c13712ee8f48207b2a0825f8a4e4e26a~'
    """
    return encode_uri_triple(triple.as_uri_triple(converter), negate=negate)


def encode_curie_triple(
    curie_triple: tuple[str, str, str], converter: Converter, *, negate: bool = False
) -> str:
    """Encode a subject-predicate-object CURIE triple.

    :param curie_triple: A triple of CURIEs represented as strings
    :param converter: A converter
    :param negate: If true, considers the triple as "negative" and postpends a ``~`` to
        the hash

    :returns: An encoded triple of URIs

    .. seealso::

        https://ts4nfdi.github.io/mapping-sameness-identifier/

    >>> import curies
    >>> from curies.triples import Triple
    >>> converter = curies.load_prefix_map(
    ...     {
    ...         "mesh": "http://id.nlm.nih.gov/mesh/",
    ...         "skos": "http://www.w3.org/2004/02/skos/core#",
    ...         "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
    ...     }
    ... )
    >>> triple = ("mesh:C000089", "skos:exactMatch", "CHEBI:28646")
    >>> encode_curie_triple(triple, converter)
    '36a1f9244ea7641a90987c82f33c25c0c13712ee8f48207b2a0825f8a4e4e26a'
    >>> encode_curie_triple(triple, converter, negate=True)
    '36a1f9244ea7641a90987c82f33c25c0c13712ee8f48207b2a0825f8a4e4e26a~'
    """
    uri_triple = (
        converter.expand(curie_triple[0], strict=True),
        converter.expand(curie_triple[1], strict=True),
        converter.expand(curie_triple[2], strict=True),
    )
    return encode_uri_triple(uri_triple, negate=negate)


def encode_uri_triple(uri_triple: tuple[str, str, str], *, negate: bool = False) -> str:
    """Encode a subject-predicate-object URI triple.

    :param uri_triple: A triple of URIs represented as strings
    :param negate: If true, considers the triple as "negative" and postpends a ``~`` to
        the hash

    :returns: An encoded triple of URIs

    .. seealso::

        https://ts4nfdi.github.io/mapping-sameness-identifier/

    >>> triple = (
    ...     "http://id.nlm.nih.gov/mesh/C000089",
    ...     "http://www.w3.org/2004/02/skos/core#exactMatch",
    ...     "http://purl.obolibrary.org/obo/CHEBI_28646",
    ... )
    >>> encode_uri_triple(triple)
    '36a1f9244ea7641a90987c82f33c25c0c13712ee8f48207b2a0825f8a4e4e26a'
    >>> encode_uri_triple(triple, negate=True)
    '36a1f9244ea7641a90987c82f33c25c0c13712ee8f48207b2a0825f8a4e4e26a~'
    """
    delimited_uris = " ".join(uri_triple)
    digest = hashlib.sha256(delimited_uris.encode("utf-8")).hexdigest()
    if negate:
        digest += "~"
    return digest
