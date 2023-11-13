"""Discovery new entries for a Converter."""

from collections import defaultdict
from typing import TYPE_CHECKING, Iterable

from curies import Converter, Record

if TYPE_CHECKING:
    import rdflib

__all__ = [
    "discover",
    "discovery_rdflib",
]


def discovery_rdflib(converter: Converter, graph: "rdflib.Graph"):
    """Discover new URI prefixes from an RDFLib triple store."""
    return discover(converter, set(_yield_uris(graph)))


def _yield_uris(graph: "rdflib.Graph") -> Iterable[str]:
    import rdflib

    for parts in graph.triples():
        for part in parts:
            if isinstance(part, rdflib.URIRef):
                yield str(part)


def discover(
    converter: Converter,
    uris: Iterable[str],
    delimiters="#/",
    cutoff: int = 30,
    metaprefix: str = "ns",
) -> Converter:
    """Discover new URI prefixes.

    :param converter: A converter with pre-existing definitions. URI prefixes
        are considered "new" if they can't already be validated by this converter
    :param uris: An iterable of URIs to search through. Will be taken as a set and
        each unique entry is only considered once.
    :param delimiters:
        The delimiters considered between a putative URI prefix and putative
        local unique identifier. By default, checks ``#`` first since this is
        commonly used for URL fragments, then ``/`` since many URIs are constructed
        with these.
    :param cutoff: The number of unique URIs with a given prefix needed to call it
        as unique. This can be adjusted, but is initially high.
    :param metaprefix: The beginning part of each dummy prefix, followed by a number
    :returns: A converter with dummy prefixes
    """
    counter = defaultdict(set)
    for uri in uris:
        if converter.is_uri(uri):
            continue
        for delimiter in delimiters:
            if delimiter not in uri:
                continue
            uri_prefix, luid = uri.rsplit(delimiter, maxsplit=1)
            if luid.isalnum():
                counter[uri_prefix + delimiter].add(luid)
                break
    counter = dict(counter)
    records = []
    record_number = 0
    for uri_prefix, luids in sorted(counter.items()):
        if len(luids) > cutoff:
            record_number += 1
            prefix = f"{metaprefix}{record_number}"
            records.append(Record(prefix=prefix, uri_prefix=uri_prefix))
    return Converter(records)
