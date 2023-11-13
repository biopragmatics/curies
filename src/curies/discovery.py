"""Discovery new entries for a Converter."""

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Optional, Sequence, Set, Union

from curies import Converter, Record

if TYPE_CHECKING:
    import rdflib

__all__ = [
    "discover",
    "discover_from_rdf",
]


def discover_from_rdf(
    converter: Converter,
    graph: Union[str, "rdflib.Graph"],
    graph_format: Optional[str] = None,
    **kwargs: Any,
) -> Converter:
    """Discover new URI prefixes from an RDFLib triple store, wrapping :func:`curies.discover`."""
    graph = _ensure_graph(graph, graph_format)
    uris = set(_yield_uris(graph))
    return discover(converter, uris, **kwargs)


def _ensure_graph(
    graph: Union[str, "rdflib.Graph"], graph_format: Optional[str] = None
) -> "rdflib.Graph":
    if not isinstance(graph, str):
        return graph
    import rdflib

    rv = rdflib.Graph()
    rv.parse(graph, format=graph_format)
    return rv


def _yield_uris(graph: "rdflib.Graph") -> Iterable[str]:
    import rdflib

    for parts in graph.triples((None, None, None)):
        for part in parts:
            if isinstance(part, rdflib.URIRef):
                yield str(part)


def discover(
    converter: Converter,
    uris: Iterable[str],
    delimiters: Sequence[str] = "#/",
    cutoff: int = 30,
    metaprefix: str = "ns",
) -> Converter:
    """Discover new URI prefixes.

    :param converter:
        A converter with pre-existing definitions. URI prefixes
        are considered "new" if they can't already be validated by this converter
    :param uris:
        An iterable of URIs to search through. Will be taken as a set and
        each unique entry is only considered once.
    :param delimiters:
        The delimiters considered between a putative URI prefix and putative
        local unique identifier. By default, checks ``#`` first since this is
        commonly used for URL fragments, then ``/`` since many URIs are constructed
        with these.
    :param cutoff:
        The number of unique URIs with a given prefix needed to call it
        as unique. This can be adjusted, but is initially high.
    :param metaprefix:
        The beginning part of each dummy prefix, followed by a number. The default value
        is ``ns``, so dummy prefixes are named ``ns1``, ``ns2``, and so on.
    :returns:
        A converter with dummy prefixes
    """
    counter = discover_helper(converter=converter, uris=uris, delimiters=delimiters)
    records = []
    record_number = 0
    for uri_prefix, luids in sorted(counter.items()):
        if len(luids) > cutoff:
            record_number += 1
            prefix = f"{metaprefix}{record_number}"
            records.append(Record(prefix=prefix, uri_prefix=uri_prefix))
    return Converter(records)


def discover_helper(
    converter: Converter, uris: Iterable[str], delimiters: Sequence[str] = "#/"
) -> Mapping[str, Set[str]]:
    """Discover new URI prefixes.

    :param converter:
        A converter with pre-existing definitions. URI prefixes
        are considered "new" if they can't already be validated by this converter
    :param uris:
        An iterable of URIs to search through. Will be taken as a set and
        each unique entry is only considered once.
    :param delimiters:
        The delimiters considered between a putative URI prefix and putative
        local unique identifier. By default, checks ``#`` first since this is
        commonly used for URL fragments, then ``/`` since many URIs are constructed
        with these.
    :returns:
        A dictionary of putative URI prefixes to sets of putative local unique identifiers
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
    return dict(counter)
