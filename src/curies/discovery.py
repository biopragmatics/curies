"""Discovery new entries for a Converter."""

from collections import defaultdict
from pathlib import PurePath
from typing import IO, TYPE_CHECKING, Any, Iterable, Mapping, Optional, Sequence, Set, TextIO, Union

from typing_extensions import Literal

from curies import Converter, Record

if TYPE_CHECKING:
    import rdflib

__all__ = [
    "discover",
    "discover_from_rdf",
]


GraphFormats = Literal["turtle", "xml", "n3", "nt", "trix"]
GraphInput = Union[IO[bytes], TextIO, "rdflib.parser.InputSource", str, bytes, PurePath]


def discover_from_rdf(
    converter: Converter,
    graph: Union[GraphInput, "rdflib.Graph"],
    *,
    format: Optional[GraphFormats] = None,
    **kwargs: Any,
) -> Converter:
    """Discover new URI prefixes from RDF content via :mod:`rdflib`.

    :param converter:
        A converter with pre-existing definitions. URI prefixes
        are considered "new" if they can't already be validated by this converter
    :param graph:
        Either a pre-instantiated RDFlib graph, or an input type to the ``source``
        keyword of :meth:`rdflib.Graph.parse`. This can be one of the following:

        - A string or bytes representation of a URL
        - A string, bytes, or Path representation of a local file
        - An I/O object that can be read directly
        - An open XML reader from RDFlib (:class:`rdflib.parser.InputSource`)
    :param format: If ``graph`` is given as a URL or I/O object, this
        is passed through to the ``format`` keyword of :meth:`rdflib.Graph.parse`.
        If none is given, defaults to ``turtle``.
    :param kwargs: Keyword arguments passed through to :func:`discover`
    :returns:
        A converter with dummy prefixes for URI prefixes appearing in the RDF
        content (i.e., triples).
    """
    graph = _ensure_graph(graph=graph, format=format)
    uris = set(_yield_uris(graph=graph))
    return discover(converter, uris, **kwargs)


def _ensure_graph(
    *, graph: Union[GraphInput, "rdflib.Graph"], format: Optional[GraphFormats] = None
) -> "rdflib.Graph":
    import rdflib

    if isinstance(graph, rdflib.Graph):
        return graph

    rv = rdflib.Graph()
    rv.parse(source=graph, format=format)
    return rv


def _yield_uris(*, graph: "rdflib.Graph") -> Iterable[str]:
    import rdflib

    for parts in graph.triples((None, None, None)):
        for part in parts:
            if isinstance(part, rdflib.URIRef):
                yield str(part)


def discover(
    converter: Converter,
    uris: Iterable[str],
    *,
    delimiters: Optional[Sequence[str]] = None,
    cutoff: Optional[int] = None,
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
        If given, will require more than ``cutoff`` unique local unique identifiers
        associated with a given URI prefix to keep it.

        Defaults to zero, which increases recall (i.e., likelihood of getting all
        possible URI prefixes) but decreases precision (i.e., more of the results
        might be false positives / spurious). If you get a lot of false positives,
        try increasing first to 1, 2, then maybe higher.
    :param metaprefix:
        The beginning part of each dummy prefix, followed by a number. The default value
        is ``ns``, so dummy prefixes are named ``ns1``, ``ns2``, and so on.
    :returns:
        A converter with dummy prefixes
    """
    if cutoff is None:
        cutoff = 0
    uri_prefix_to_luids = _get_uri_prefix_to_luids(
        converter=converter, uris=uris, delimiters=delimiters
    )
    uri_prefixes = [
        uri_prefix
        for uri_prefix, luids in sorted(uri_prefix_to_luids.items())
        # If the cutoff is 5, and only 3 unique LUIDs with the URI prefix
        # were identified, we're going to disregard this URI prefix.
        if len(luids) >= cutoff
    ]
    records = [
        Record(prefix=f"{metaprefix}{uri_prefix_index}", uri_prefix=uri_prefix)
        for uri_prefix_index, uri_prefix in enumerate(uri_prefixes, start=1)
    ]
    return Converter(records)


#: The default delimiters used when guessing URI prefixes
DEFAULT_DELIMITERS = ("#", "/", "_")


def _get_uri_prefix_to_luids(
    *, converter: Converter, uris: Iterable[str], delimiters: Optional[Sequence[str]] = None
) -> Mapping[str, Set[str]]:
    """Get a mapping from putative URI prefixes to corresponding putative local unique identifiers.

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
    if not delimiters:
        delimiters = DEFAULT_DELIMITERS
    uri_prefix_to_luids = defaultdict(set)
    for uri in uris:
        if converter.is_uri(uri):
            continue
        if uri.startswith("https://github.com") and "issues" in uri:
            # TODO it's not really the job of :mod:`curies` to incorporate special cases,
            #  but the GitHub thing is such an annoyance...
            continue
        for delimiter in delimiters:
            if delimiter not in uri:
                continue
            uri_prefix, luid = uri.rsplit(delimiter, maxsplit=1)
            if luid.isalnum():
                uri_prefix_to_luids[uri_prefix + delimiter].add(luid)
                break
    return dict(uri_prefix_to_luids)
