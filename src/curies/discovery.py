"""Discovery new entries for a Converter.

The :func:`curies.discover` functionality is intended to be used in a "data science"
workflow. Its goal is to enable a data scientist to semi-interactively explore data
(e.g., coming from an ontology, SSSOM, RDF) that doesn't come with a complete (extended)
prefix map and identify common URI prefixes.

It returns the discovered URI prefixes in a :class:`curies.Converter` object with
"dummy" CURIE prefixes. This makes it possible to convert the URIs appearing in the data
into CURIEs and therefore enables their usage in places where CURIEs are expected.

However, it's suggested that after discovering URI prefixes, the data scientist more
carefully constructs a meaningful prefix map based on the discovered one. This might
include some or all of the following steps:

1. Replace dummy CURIE prefixes with meaningful ones
2. Remove spurious URI prefixes that appear but do not represent a semantic space. This
   happens often due to using ``_`` as a delimiter or having a frequency cutoff of zero
   (see the parameters for this function).
3. Consider chaining a comprehensive extended prefix map such as the Bioregistry (from
   :func:`curies.get_bioregistry_converter`) with onto the converter passed to this
   function so pre-existing URI prefixes are not *re-discovered*.

Finally, you should save the prefix map that you create in a persistent place (i.e.,
inside a JSON file) such that it can be reused.

Algorithm
=========

The :func:`curies.discover` function implements the following algorithm that does the
following for each URI:

1. For each delimiter (in the priority order they are given) check if the delimiter is
   present.
2. If it's present, split the URI into two parts based on rightmost appearance of the
   delimiter.
3. If the right part after splitting is all alphanumeric characters, save the URI prefix
   (with delimiter attached)
4. If a delimiter is successfully used to identify a URI prefix, don't check any of the
   following delimiters

After identifying putative URI prefixes, the second part of the algorithm does the
following:

1. If a cutoff was provided, remove all putative URI prefixes for which there were fewer
   examples than the cutoff
2. Sort the URI prefixes lexicographically (i.e., with :func:`sorted`)
3. Assign a dummy CURIE prefix to each URI prefix, counting upwards from 1
4. Construct a converter from this prefix map and return it
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import PurePath
from typing import IO, TYPE_CHECKING, Any, TextIO, Union

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
    graph: GraphInput | rdflib.Graph,
    *,
    format: GraphFormats | None = None,
    **kwargs: Any,
) -> Converter:
    """Discover new URI prefixes from RDF content via :mod:`rdflib`.

    This function works the same as :func:`discover`, but gets its URI list from a
    triple store. See :func:`discover` for a more detailed explanation of how this
    algorithm works.

    :param graph: Either a pre-instantiated RDFlib graph, or an input type to the
        ``source`` keyword of :meth:`rdflib.Graph.parse`. This can be one of the
        following:

        - A string or bytes representation of a URL
        - A string, bytes, or Path representation of a local file
        - An I/O object that can be read directly
        - An open XML reader from RDFlib (:class:`rdflib.parser.InputSource`)
    :param format: If ``graph`` is given as a URL or I/O object, this is passed through
        to the ``format`` keyword of :meth:`rdflib.Graph.parse`. If none is given,
        defaults to ``turtle``.
    :param kwargs: Keyword arguments passed through to :func:`discover`

    :returns: A converter with dummy prefixes for URI prefixes appearing in the RDF
        content (i.e., triples).
    """
    uris = get_uris_from_rdf(graph=graph, format=format)
    return discover(uris, **kwargs)


def get_uris_from_rdf(
    graph: GraphInput | rdflib.Graph, *, format: GraphFormats | None = None
) -> set[str]:
    """Get a set of URIs from a graph."""
    graph = _ensure_graph(graph=graph, format=format)
    return set(_yield_uris(graph=graph))


def _ensure_graph(
    *, graph: GraphInput | rdflib.Graph, format: GraphFormats | None = None
) -> rdflib.Graph:
    import rdflib

    if not isinstance(graph, rdflib.Graph):
        _temp_graph = rdflib.Graph()
        _temp_graph.parse(source=graph, format=format)
        graph = _temp_graph

    return graph


def _yield_uris(*, graph: rdflib.Graph) -> Iterable[str]:
    import rdflib

    for parts in graph.triples((None, None, None)):
        for part in parts:
            if isinstance(part, rdflib.URIRef):
                yield str(part)


def discover(
    uris: Iterable[str],
    *,
    delimiters: Sequence[str] | None = None,
    cutoff: int | None = None,
    metaprefix: str = "ns",
    converter: Converter | None = None,
) -> Converter:
    """Discover new URI prefixes and construct a converter with a unique dummy CURIE prefix for each.

    :param uris: An iterable of URIs to search through. Will be taken as a set and each
        unique entry is only considered once.
    :param delimiters: The character(s) that delimit a URI prefix from a local unique
        identifier. If none given, defaults to using ``/``, ``#``, and ``_``. For
        example:

        - ``/`` is the delimiter in ``https://www.ncbi.nlm.nih.gov/pubmed/37929212``,
          which separates the URI prefix ``https://www.ncbi.nlm.nih.gov/pubmed/`` from
          the local unique identifier `37929212
          <https://www.ncbi.nlm.nih.gov/pubmed/37929212>`_ for the article "New insights
          into osmobiosis and chemobiosis in tardigrades" in PubMed.
        - ``#`` is the delimiter in ``http://www.w3.org/2000/01/rdf-schema#label``,
          which separates the URI prefix ``http://www.w3.org/2000/01/rdf-schema#`` from
          the local unique identifier `label
          <http://www.w3.org/2000/01/rdf-schema#label>`_ for the term "label" in the RDF
          Schema. The ``#`` typically is used in a URL to denote a fragment and commonly
          appears in small semantic web vocabularies that are shown as a single HTML
          page.
        - ``_`` is the delimiter in ``http://purl.obolibrary.org/obo/GO_0032571``, which
          separates the URI prefix ``http://purl.obolibrary.org/obo/GO_`` from the local
          unique identifier `0032571 <http://purl.obolibrary.org/obo/GO_0032571>`_ for
          the term "response to vitamin K" in the Gene Ontology

        .. note::

            The delimiter is itself a part of the URI prefix

    :param cutoff: If given, will require more than ``cutoff`` unique local unique
        identifiers associated with a given URI prefix to keep it.

        Defaults to zero, which increases recall (i.e., likelihood of getting all
        possible URI prefixes) but decreases precision (i.e., more of the results might
        be false positives / spurious). If you get a lot of false positives, try
        increasing first to 1, 2, then maybe higher.
    :param metaprefix: The beginning part of each dummy prefix, followed by a number.
        The default value is ``ns``, so dummy prefixes are named ``ns1``, ``ns2``, and
        so on.
    :param converter: If a pre-existing converter is passed, then URIs that can be
        parsed using the pre-existing converter are not considered during discovery.

        For example, if you're an OBO person working with URIs coming from an OBO
        ontology, it makes sense to pass the converter from
        :func:`curies.get_obo_converter` to reduce false positive discoveries. More
        generally, a comprehensive converter like the Bioregistry (from
        :func:`curies.get_bioregistry_converter`) can massively reduce false positive
        discoveries and ultimately reduce burden on the data scientist using this
        function when needing to understand the results and carefully curate a prefix
        map based on the discoveries.

    :returns: A converter with dummy prefixes

    >>> import curies
    >>> # Generate some example URIs
    >>> uris = [f"http://ran.dom/{i:03}" for i in range(30)]
    >>> discovered_converter = curies.discover(uris)
    >>> discovered_converter.records
    [Record(prefix="ns1", uri_prefix="http://ran.dom/")]
    >>> # Now, you can compress the URIs to dummy CURIEs
    >>> discovered_converter.compress("http://ran.dom/002")
    'ns1:002'

    """
    uri_prefix_to_luids = _get_uri_prefix_to_luids(
        converter=converter, uris=uris, delimiters=delimiters
    )
    uri_prefixes = [
        uri_prefix
        for uri_prefix, luids in sorted(uri_prefix_to_luids.items())
        # If the cutoff is 5, and only 3 unique LUIDs with the URI prefix
        # were identified, we're going to disregard this URI prefix.
        if cutoff is None or len(luids) >= cutoff
    ]
    records = [
        Record(prefix=f"{metaprefix}{uri_prefix_index}", uri_prefix=uri_prefix)
        for uri_prefix_index, uri_prefix in enumerate(uri_prefixes, start=1)
    ]
    return Converter(records)


#: The default delimiters used when guessing URI prefixes
DEFAULT_DELIMITERS = ("#", "/", "_")


def _get_uri_prefix_to_luids(
    *,
    converter: Converter | None = None,
    uris: Iterable[str],
    delimiters: Sequence[str] | None = None,
) -> Mapping[str, set[str]]:
    """Get a mapping from putative URI prefixes to corresponding putative local unique identifiers.

    :param converter: A converter with pre-existing definitions. URI prefixes are
        considered "new" if they can't already be validated by this converter
    :param uris: An iterable of URIs to search through. Will be taken as a set and each
        unique entry is only considered once.
    :param delimiters: The delimiters considered between a putative URI prefix and
        putative local unique identifier. By default, checks ``#`` first since this is
        commonly used for URL fragments, then ``/`` since many URIs are constructed with
        these.

    :returns: A dictionary of putative URI prefixes to sets of putative local unique
        identifiers
    """
    if not delimiters:
        delimiters = DEFAULT_DELIMITERS
    uri_prefix_to_luids = defaultdict(set)
    for uri in uris:
        if converter is not None and converter.is_uri(uri):
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
