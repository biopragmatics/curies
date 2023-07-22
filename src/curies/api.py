# -*- coding: utf-8 -*-

"""Data structures and algorithms for :mod:`curies`."""

import csv
import itertools as itt
import json
from collections import defaultdict
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Collection,
    DefaultDict,
    Dict,
    Iterable,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)

import requests
from pydantic import BaseModel, Field, validator
from pytrie import StringTrie

if TYPE_CHECKING:  # pragma: no cover
    import pandas
    import rdflib

__all__ = [
    "Converter",
    "Reference",
    "ReferenceTuple",
    "Record",
    "DuplicateValueError",
    "DuplicatePrefixes",
    "DuplicateURIPrefixes",
    "chain",
]

X = TypeVar("X")
LocationOr = Union[str, Path, X]


class ReferenceTuple(NamedTuple):
    """A reference to an entity in a given identifier space.

    This derives from the "named tuple" which means that it acts
    like a tuple in most senses - it can be hashed and unpacked
    like most other tuples. Underneath, it has a C implementation
    and is very efficient.
    """

    prefix: str
    identifier: str

    @property
    def curie(self) -> str:
        """Get the reference as a CURIE string.

        :return:
            A string representation of a compact URI (CURIE).

        >>> ReferenceTuple("chebi", "1234").curie
        'chebi:1234'
        """
        return f"{self.prefix}:{self.identifier}"

    @classmethod
    def from_curie(cls, curie: str, sep: str = ":") -> "ReferenceTuple":
        """Parse a CURIE string and populate a reference tuple.

        :param curie: A string representation of a compact URI (CURIE)
        :param sep: The separator
        :return: A reference tuple

        >>> ReferenceTuple.from_curie("chebi:1234")
        ReferenceTuple(prefix='chebi', identifier='1234')
        """
        prefix, identifier = curie.split(sep, 1)
        return cls(prefix, identifier)


class Reference(BaseModel):  # type:ignore
    """A reference to an entity in a given identifier space.

    This class uses Pydantic to make it easier to build other
    more complex data types with Pydantic that also uses a first-
    class notion of parsed reference (instead of merely stringified
    CURIEs). Instances of this class can also be hashed because of the
    "frozen" configuration from Pydantic (see
    https://docs.pydantic.dev/latest/usage/model_config/ for more details).
    """

    prefix: str = Field(
        ...,
        description="The prefix used in a compact URI (CURIE).",
    )
    identifier: str = Field(
        ..., description="The local unique identifier used in a compact URI (CURIE)."
    )

    class Config:
        """Pydantic configuration for references."""

        frozen = True

    @property
    def curie(self) -> str:
        """Get the reference as a CURIE string.

        :return:
            A string representation of a compact URI (CURIE).

        >>> Reference(prefix="chebi", identifier="1234").curie
        'chebi:1234'
        """
        return f"{self.prefix}:{self.identifier}"

    @property
    def pair(self) -> ReferenceTuple:
        """Get the reference as a 2-tuple of prefix and identifier."""
        return ReferenceTuple(self.prefix, self.identifier)

    @classmethod
    def from_curie(cls, curie: str, sep: str = ":") -> "Reference":
        """Parse a CURIE string and populate a reference.

        :param curie: A string representation of a compact URI (CURIE)
        :param sep: The separator
        :return: A reference object

        >>> Reference.from_curie("chebi:1234")
        Reference(prefix='chebi', identifier='1234')
        """
        prefix, identifier = curie.split(sep, 1)
        return cls(prefix=prefix, identifier=identifier)


class Record(BaseModel):  # type:ignore
    """A record of some prefixes and their associated URI prefixes."""

    prefix: str = Field(..., description="The canonical prefix, used in the reverse prefix map")
    uri_prefix: str = Field(
        ..., description="The canonical URI prefix, used in the forward prefix map"
    )
    prefix_synonyms: List[str] = Field(default_factory=list)
    uri_prefix_synonyms: List[str] = Field(default_factory=list)

    @validator("prefix_synonyms")  # type:ignore
    def prefix_not_in_synonyms(cls, v: str, values: Mapping[str, Any]) -> str:  # noqa:N805
        """Check that the canonical prefix does not apper in the prefix synonym list."""
        prefix = values["prefix"]
        if prefix in v:
            raise ValueError(f"Duplicate of canonical prefix `{prefix}` in prefix synonyms")
        return v

    @validator("uri_prefix_synonyms")  # type:ignore
    def uri_prefix_not_in_synonyms(cls, v: str, values: Mapping[str, Any]) -> str:  # noqa:N805
        """Check that the canonical URI prefix does not apper in the URI prefix synonym list."""
        uri_prefix = values["uri_prefix"]
        if uri_prefix in v:
            raise ValueError(
                f"Duplicate of canonical URI prefix `{uri_prefix}` in URI prefix synonyms"
            )
        return v

    @property
    def _all_prefixes(self) -> List[str]:
        return [self.prefix, *self.prefix_synonyms]

    @property
    def _all_uri_prefixes(self) -> List[str]:
        return [self.uri_prefix, *self.uri_prefix_synonyms]


class DuplicateValueError(ValueError):
    """An error raised with constructing a converter with data containing duplicate values."""

    def __init__(self, duplicates: List[Tuple[Record, Record, str]]) -> None:
        """Initialize the error."""
        self.duplicates = duplicates

    def _str(self) -> str:
        s = ""
        for r1, r2, p in self.duplicates:
            s += f"\n{p}:\n\t{r1}\n\t{r2}\n"
        return s


class DuplicateURIPrefixes(DuplicateValueError):
    """An error raised with constructing a converter with data containing duplicate URI prefixes."""

    def __str__(self) -> str:  # noqa:D105
        return f"Duplicate URI prefixes:\n{self._str()}"


class DuplicatePrefixes(DuplicateValueError):
    """An error raised with constructing a converter with data containing duplicate prefixes."""

    def __str__(self) -> str:  # noqa:D105
        return f"Duplicate prefixes:\n{self._str()}"


class ConversionError(ValueError):
    """An error raised on conversion."""


class ExpansionError(ConversionError):
    """An error raised on expansion if the prefix can't be looked up."""


class CompressionError(ConversionError):
    """An error raised on expansion if the URI prefix can't be matched."""


def _get_duplicate_uri_prefixes(records: List[Record]) -> List[Tuple[Record, Record, str]]:
    return [
        (record_1, record_2, uri_prefix)
        for record_1, record_2 in itt.combinations(records, 2)
        for uri_prefix, up2 in itt.product(record_1._all_uri_prefixes, record_2._all_uri_prefixes)
        if uri_prefix == up2
    ]


def _get_duplicate_prefixes(records: List[Record]) -> List[Tuple[Record, Record, str]]:
    return [
        (record_1, record_2, prefix)
        for record_1, record_2 in itt.combinations(records, 2)
        for prefix, p2 in itt.product(record_1._all_prefixes, record_2._all_prefixes)
        if prefix == p2
    ]


def _get_prefix_map(records: List[Record]) -> Dict[str, str]:
    rv = {}
    for record in records:
        rv[record.prefix] = record.uri_prefix
        for prefix_synonym in record.prefix_synonyms:
            rv[prefix_synonym] = record.uri_prefix
    return rv


def _get_reverse_prefix_map(records: List[Record]) -> Dict[str, str]:
    rv = {}
    for record in records:
        rv[record.uri_prefix] = record.prefix
        for uri_prefix_synonym in record.uri_prefix_synonyms:
            rv[uri_prefix_synonym] = record.prefix
    return rv


def _get_prefix_synmap(records: List[Record]) -> Dict[str, str]:
    rv = {}
    for record in records:
        rv[record.prefix] = record.prefix
        for prefix_synonym in record.prefix_synonyms:
            rv[prefix_synonym] = record.prefix
    return rv


def _prepare(data: LocationOr[X]) -> X:
    if isinstance(data, Path):
        with data.open() as file:
            return cast(X, json.load(file))
    elif isinstance(data, str):
        if any(data.startswith(p) for p in ("https://", "http://", "ftp://")):
            res = requests.get(data)
            res.raise_for_status()
            return cast(X, res.json())
        with open(data) as file:
            return cast(X, json.load(file))
    else:
        return data


class Converter:
    """A cached prefix map data structure.

    .. code-block::

        # Construct a prefix map:
        >>> converter = Converter.from_prefix_map({
        ...    "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        ...    "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
        ...    "GO": "http://purl.obolibrary.org/obo/GO_",
        ...    "OBO": "http://purl.obolibrary.org/obo/",
        ... })

        # Compression and Expansion:
        >>> converter.compress("http://purl.obolibrary.org/obo/CHEBI_1")
        'CHEBI:1'
        >>> converter.expand("CHEBI:1")
        'http://purl.obolibrary.org/obo/CHEBI_1'

        # Example with unparsable URI:
        >>> converter.compress("http://example.com/missing:0000000")

        # Example with missing prefix:
        >>> converter.expand("missing:0000000")
    """

    #: The expansion dictionary with prefixes as keys and priority URI prefixes as values
    prefix_map: Dict[str, str]
    #: The mapping from URI prefixes to prefixes
    reverse_prefix_map: Dict[str, str]
    #: A prefix trie for efficient parsing of URIs
    trie: StringTrie

    def __init__(self, records: List[Record], *, delimiter: str = ":", strict: bool = True) -> None:
        """Instantiate a converter.

        :param records:
            A list of records. If you plan to build a converter incrementally, pass an empty list.
        :param strict:
            If true, raises issues on duplicate URI prefixes
        :param delimiter:
            The delimiter used for CURIEs. Defaults to a colon.
        :raises DuplicatePrefixes: if any records share any synonyms
        :raises DuplicateURIPrefixes: if any records share any URI prefixes
        """
        if strict:
            duplicate_uri_prefixes = _get_duplicate_uri_prefixes(records)
            if duplicate_uri_prefixes:
                raise DuplicateURIPrefixes(duplicate_uri_prefixes)
            duplicate_prefixes = _get_duplicate_prefixes(records)
            if duplicate_prefixes:
                raise DuplicatePrefixes(duplicate_prefixes)

        self.delimiter = delimiter
        self.records = records
        self.prefix_map = _get_prefix_map(records)
        self.synonym_to_prefix = _get_prefix_synmap(records)
        self.reverse_prefix_map = _get_reverse_prefix_map(records)
        self.trie = StringTrie(self.reverse_prefix_map)

    def _check_record(self, record: Record) -> None:
        """Check if the record can be added."""
        if record.prefix in self.prefix_map:
            raise ValueError(f"new record has duplicate prefix: {record.prefix}")
        if record.uri_prefix in self.reverse_prefix_map:
            raise ValueError(f"new record has duplicate URI prefix: {record.uri_prefix}")
        for prefix_synonym in record.prefix_synonyms:
            if prefix_synonym in self.prefix_map:
                raise ValueError(f"new record has duplicate prefix: {prefix_synonym}")
        for uri_prefix_synonym in record.uri_prefix_synonyms:
            if uri_prefix_synonym in self.reverse_prefix_map:
                raise ValueError(f"new record has duplicate URI prefix: {uri_prefix_synonym}")

    def add_record(self, record: Record) -> None:
        """Append a record to the converter."""
        self._check_record(record)

        self.records.append(record)
        self.prefix_map[record.prefix] = record.uri_prefix
        self.synonym_to_prefix[record.prefix] = record.prefix
        for prefix_synonym in record.prefix_synonyms:
            self.prefix_map[prefix_synonym] = record.uri_prefix
            self.synonym_to_prefix[prefix_synonym] = record.prefix

        self.reverse_prefix_map[record.uri_prefix] = record.prefix
        self.trie[record.uri_prefix] = record.prefix
        for uri_prefix_synonym in record.uri_prefix_synonyms:
            self.reverse_prefix_map[uri_prefix_synonym] = record.prefix
            self.trie[uri_prefix_synonym] = record.prefix

    def add_prefix(
        self,
        prefix: str,
        uri_prefix: str,
        prefix_synonyms: Optional[Collection[str]] = None,
        uri_prefix_synonyms: Optional[Collection[str]] = None,
    ) -> None:
        """Append a prefix to the converter.

        :param prefix:
            The prefix to append, e.g., ``go``
        :param uri_prefix:
            The URI prefix to append, e.g., ``http://purl.obolibrary.org/obo/GO_``
        :param prefix_synonyms:
            An optional collection of synonyms for the prefix such as ``gomf``, ``gocc``, etc.
        :param uri_prefix_synonyms:
            An optional collections of synonyms for the URI prefix such as
            ``https://bioregistry.io/go:``, ``http://www.informatics.jax.org/searches/GO.cgi?id=GO:``, etc.

        This can be used to add missing namespaces on-the-fly to an existing converter:

        >>> import curies
        >>> converter = curies.get_obo_converter()
        >>> converter.add_prefix("hgnc", "https://bioregistry.io/hgnc:")
        >>> converter.expand("hgnc:1234")
        'https://bioregistry.io/hgnc:1234'
        >>> converter.expand("GO:0032571 ")
        'http://purl.obolibrary.org/obo/GO_0032571'

        This can also be used to incrementally build up a converter from scratch:

        >>> import curies
        >>> converter = curies.Converter(records=[])
        >>> converter.add_prefix("hgnc", "https://bioregistry.io/hgnc:")
        >>> converter.expand("hgnc:1234")
        'https://bioregistry.io/hgnc:1234'
        """
        record = Record(
            prefix=prefix,
            uri_prefix=uri_prefix,
            prefix_synonyms=sorted(prefix_synonyms or []),
            uri_prefix_synonyms=sorted(uri_prefix_synonyms or []),
        )
        self.add_record(record)

    @classmethod
    def from_extended_prefix_map(
        cls, records: LocationOr[Iterable[Union[Record, Dict[str, Any]]]], **kwargs: Any
    ) -> "Converter":
        """Get a converter from a list of dictionaries by creating records out of them.

        :param records: An iterable of :class:`Record` objects or dictionaries that will
            get converted into record objects
        :param kwargs: Keyword arguments to pass to the parent class's init
        :returns: A converter

        An extended prefix map is a list of dictionaries containing four keys:

        1. A ``prefix`` string
        2. A ``uri_prefix`` string
        3. An optional list of strings ``prefix_synonyms``
        4. An optional list of strings ``uri_prefix_synonyms``

        Across the whole list of dictionaries, there should be uniqueness within
        the union of all ``prefix`` and ``prefix_synonyms`` as well as uniqueness
        within the union of all ``uri_prefix`` and ``uri_prefix_synonyms``.

        >>> epm = [
        ...     {
        ...         "prefix": "CHEBI",
        ...         "prefix_synonyms": ["chebi", "ChEBI"],
        ...         "uri_prefix": "http://purl.obolibrary.org/obo/CHEBI_",
        ...         "uri_prefix_synonyms": ["https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:"],
        ...     },
        ...     {
        ...         "prefix": "GO",
        ...         "uri_prefix": "http://purl.obolibrary.org/obo/GO_",
        ...     },
        ... ]
        >>> converter = Converter.from_extended_prefix_map(epm)
        # Canonical prefix
        >>> converter.expand("CHEBI:138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'
        # Prefix synoynm
        >>> converter.expand("chebi:138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'
        # Canonical URI prefix
        >>> converter.compress("http://purl.obolibrary.org/obo/CHEBI_138488")
        'CHEBI:138488'
        # URI prefix synoynm
        >>> converter.compress("https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:138488")
        'CHEBI:138488'

        Example from a remote source:

        >>> url = "https://github.com/biopragmatics/bioregistry/raw/main/exports/contexts/bioregistry.epm.json"
        >>> converter = Converter.from_extended_prefix_map(url)
        """
        return cls(
            records=[
                record if isinstance(record, Record) else Record(**record)
                for record in _prepare(records)
            ],
            **kwargs,
        )

    @classmethod
    def from_priority_prefix_map(
        cls, data: LocationOr[Mapping[str, List[str]]], **kwargs: Any
    ) -> "Converter":
        """Get a converter from a priority prefix map.

        :param data:
            A prefix map where the keys are prefixes (e.g., `chebi`)
            and the values are lists of URI prefixes (e.g., ``http://purl.obolibrary.org/obo/CHEBI_``)
            with the first element of the list being the priority URI prefix for expansions.
        :param kwargs: Keyword arguments to pass to the parent class's init
        :returns: A converter

        >>> priority_prefix_map = {
        ...     "CHEBI": [
        ...         "http://purl.obolibrary.org/obo/CHEBI_",
        ...         "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:",
        ...     ],
        ...     "GO": ["http://purl.obolibrary.org/obo/GO_"],
        ...     "obo": ["http://purl.obolibrary.org/obo/"],
        ... }
        >>> converter = Converter.from_priority_prefix_map(priority_prefix_map)
        >>> converter.expand("CHEBI:138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'
        >>> converter.compress("http://purl.obolibrary.org/obo/CHEBI_138488")
        'CHEBI:138488'
        >>> converter.compress("https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:138488")
        'CHEBI:138488'
        """
        return cls(
            [
                Record(
                    prefix=prefix, uri_prefix=uri_prefixes[0], uri_prefix_synonyms=uri_prefixes[1:]
                )
                for prefix, uri_prefixes in _prepare(data).items()
            ],
            **kwargs,
        )

    @classmethod
    def from_prefix_map(
        cls, prefix_map: LocationOr[Mapping[str, str]], **kwargs: Any
    ) -> "Converter":
        """Get a converter from a simple prefix map.

        :param prefix_map:
            A mapping whose keys are prefixes and whose values are the corresponding *URI prefixes*).

            .. note::

                It's possible that some *URI prefixes* (values in this mapping)
                partially overlap (e.g., ``http://purl.obolibrary.org/obo/GO_`` for the prefix ``GO`` and
                ``http://purl.obolibrary.org/obo/`` for the prefix ``OBO``). The longest URI prefix will always
                be matched. For example, parsing ``http://purl.obolibrary.org/obo/GO_0032571``
                will return ``GO:0032571`` instead of ``OBO:GO_0032571``.
        :param kwargs: Keyword arguments to pass to :func:`Converter.__init__`
        :returns:
            A converter

        >>> converter = Converter.from_prefix_map({
        ...     "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        ...     "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
        ...     "GO": "http://purl.obolibrary.org/obo/GO_",
        ...     "OBO": "http://purl.obolibrary.org/obo/",
        ... })
        >>> converter.expand("CHEBI:138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'
        >>> converter.compress("http://purl.obolibrary.org/obo/CHEBI_138488")
        'CHEBI:138488'
        """
        return cls(
            [
                Record(prefix=prefix, uri_prefix=uri_prefix)
                for prefix, uri_prefix in _prepare(prefix_map).items()
            ],
            **kwargs,
        )

    @classmethod
    def from_reverse_prefix_map(
        cls, reverse_prefix_map: LocationOr[Mapping[str, str]]
    ) -> "Converter":
        """Get a converter from a reverse prefix map.

        :param reverse_prefix_map:
            A mapping whose keys are URI prefixes and whose values are the corresponding prefixes.
            This data structure allow for multiple different URI formats to point to the same
            prefix.

            .. note::

                It's possible that some *URI prefixes* (keys in this mapping)
                partially overlap (e.g., ``http://purl.obolibrary.org/obo/GO_`` for the prefix ``GO`` and
                ``http://purl.obolibrary.org/obo/`` for the prefix ``OBO``). The longest URI prefix will always
                be matched. For example, parsing ``http://purl.obolibrary.org/obo/GO_0032571``
                will return ``GO:0032571`` instead of ``OBO:GO_0032571``.
        :return:
            A converter

        >>> converter = Converter.from_reverse_prefix_map({
        ...     "http://purl.obolibrary.org/obo/CHEBI_": "CHEBI",
        ...     "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=": "CHEBI",
        ...     "http://purl.obolibrary.org/obo/MONDO_": "MONDO",
        ... })
        >>> converter.expand("CHEBI:138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'
        >>> converter.compress("http://purl.obolibrary.org/obo/CHEBI_138488")
        'CHEBI:138488'
        >>> converter.compress("https://www.ebi.ac.uk/chebi/searchId.do?chebiId=138488")
        'CHEBI:138488'

        Altenatively, get content from the internet like

        >>> url = "https://github.com/biopragmatics/bioregistry/raw/main/exports/contexts/bioregistry.rpm.json"
        >>> converter = Converter.from_reverse_prefix_map(url)
        >>> "chebi" in Converter.prefix_map
        """
        dd = defaultdict(list)
        for uri_prefix, prefix in _prepare(reverse_prefix_map).items():
            dd[prefix].append(uri_prefix)
        records = []
        for prefix, uri_prefixes in dd.items():
            uri_prefix, *uri_prefix_synonyms = sorted(uri_prefixes, key=len)
            records.append(
                Record(
                    prefix=prefix, uri_prefix=uri_prefix, uri_prefix_synonyms=uri_prefix_synonyms
                )
            )
        return cls(records)

    @classmethod
    def from_jsonld(cls, data: LocationOr[Dict[str, Any]]) -> "Converter":
        """Get a converter from a JSON-LD object, which contains a prefix map in its ``@context`` key.

        :param data:
            A JSON-LD object
        :return:
            A converter

        Example from a remote context file:

        >>> base = "https://raw.githubusercontent.com"
        >>> url = f"{base}/biopragmatics/bioregistry/main/exports/contexts/semweb.context.jsonld"
        >>> converter = Converter.from_jsonld(url)
        >>> "rdf" in converter.prefix_map
        """
        return cls.from_prefix_map(_prepare(data)["@context"])

    @classmethod
    def from_jsonld_github(
        cls, owner: str, repo: str, *path: str, branch: str = "main"
    ) -> "Converter":
        """Construct a remote JSON-LD URL on GitHub then parse with :meth:`Converter.from_jsonld`.

        :param owner: A github repository owner or organization (e.g., ``biopragmatics``)
        :param repo: The name of the repository (e.g., ``bioregistry``)
        :param path: The file path in the GitHub repository to a JSON-LD context file.
        :param branch: The branch from which the file should be downloaded. Defaults to ``main``, for old
            repositories this might need to be changed to ``master``.
        :return:
            A converter
        :raises ValueError:
            If the given path doesn't end in a .jsonld file name

        >>> converter = Converter.from_jsonld_github(
        ...     "biopragmatics", "bioregistry", "exports",
        ...     "contexts", "semweb.context.jsonld",
        ... )
        >>> "rdf" in converter.prefix_map
        True
        """
        if not path or not path[-1].endswith(".jsonld"):
            raise ValueError("final path argument should end with .jsonld")
        rest = "/".join(path)
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{rest}"
        return cls.from_jsonld(url)

    @classmethod
    def from_rdflib(
        cls,
        graph_or_manager: Union["rdflib.Graph", "rdflib.namespace.NamespaceManager"],
        **kwargs: Any,
    ) -> "Converter":
        """Get a converter from an RDFLib graph or namespace manager.

        :param graph_or_manager: A RDFLib graph or manager object
        :param kwargs: Keyword arguments to pass to :meth:`from_prefix_map`
        :return: A converter

        In the following example, a :class:`rdflib.Graph` is created, a namespace
        is bound to it, then a converter is made:

        >>> import rdflib, curies
        >>> graph = rdflib.Graph()
        >>> graph.bind("hgnc", "https://bioregistry.io/hgnc:")
        >>> converter = curies.Converter.from_rdflib(graph)
        >>> converter.expand("hgnc:1234")
        'https://bioregistry.io/hgnc:1234'

        This also works if you directly start with a :class:`rdflib.namespace.NamespaceManager`:

        >>> converter = curies.Converter.from_rdflib(graph.namespace_manager)
        >>> converter.expand("hgnc:1234")
        'https://bioregistry.io/hgnc:1234'
        """
        # it's required to stringify namespace since it's a rdflib.URIRef
        # object, which acts funny if not coerced into a string
        prefix_map = {prefix: str(namespace) for prefix, namespace in graph_or_manager.namespaces()}
        return cls.from_prefix_map(prefix_map, **kwargs)

    def get_prefixes(self) -> Set[str]:
        """Get the set of prefixes covered by this converter."""
        return {record.prefix for record in self.records}

    def format_curie(self, prefix: str, identifier: str) -> str:
        """Format a prefix and identifier into a CURIE string."""
        return f"{prefix}{self.delimiter}{identifier}"

    def compress_strict(self, uri: str) -> str:
        """Compress a URI to a CURIE, and raise an error of not possible."""
        rv = self.compress(uri)
        if rv is None:
            raise CompressionError(uri)
        return rv

    def compress(self, uri: str) -> Optional[str]:
        """Compress a URI to a CURIE, if possible.

        :param uri:
            A string representing a valid uniform resource identifier (URI)
        :returns:
            A compact URI if this converter could find an appropriate URI prefix, otherwise none.

        >>> from curies import Converter
        >>> converter = Converter.from_prefix_map({
        ...    "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        ...    "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
        ...    "GO": "http://purl.obolibrary.org/obo/GO_",
        ... })
        >>> converter.compress("http://purl.obolibrary.org/obo/CHEBI_138488")
        'CHEBI:138488'
        >>> converter.compress("http://example.org/missing:0000000")
        """
        prefix, identifier = self.parse_uri(uri)
        if prefix is None or identifier is None:
            return None
        return self.format_curie(prefix, identifier)

    def parse_uri(self, uri: str) -> Union[ReferenceTuple, Tuple[None, None]]:
        """Compress a URI to a CURIE pair.

        :param uri:
            A string representing a valid uniform resource identifier (URI)
        :returns:
            A CURIE pair if the URI could be parsed, otherwise a pair of None's

        >>> from curies import Converter
        >>> converter = Converter.from_prefix_map({
        ...    "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        ...    "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
        ...    "GO": "http://purl.obolibrary.org/obo/GO_",
        ... })
        >>> converter.parse_uri("http://purl.obolibrary.org/obo/CHEBI_138488")
        ('CHEBI', '138488')
        >>> converter.parse_uri("http://example.org/missing:0000000")
        (None, None)
        """
        try:
            value, prefix = self.trie.longest_prefix_item(uri)
        except KeyError:
            return None, None
        else:
            return ReferenceTuple(prefix, uri[len(value) :])

    def expand_strict(self, curie: str) -> str:
        """Expand a CURIE to a URI, and raise an error of not possible."""
        rv = self.expand(curie)
        if rv is None:
            raise ExpansionError(curie)
        return rv

    def expand(self, curie: str) -> Optional[str]:
        """Expand a CURIE to a URI, if possible.

        :param curie:
            A string representing a compact URI
        :returns:
            A URI if this converter contains a URI prefix for the prefix in this CURIE

        >>> from curies import Converter
        >>> converter = Converter.from_prefix_map({
        ...    "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        ...    "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
        ...    "GO": "http://purl.obolibrary.org/obo/GO_",
        ... })
        >>> converter.expand("CHEBI:138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'
        >>> converter.expand("missing:0000000")

        .. note::

            If there are partially overlapping *URI prefixes* in this converter
            (e.g., ``http://purl.obolibrary.org/obo/GO_`` for the prefix ``GO`` and
            ``http://purl.obolibrary.org/obo/`` for the prefix ``OBO``), the longest
            URI prefix will always be matched. For example, parsing
            ``http://purl.obolibrary.org/obo/GO_0032571`` will return ``GO:0032571``
            instead of ``OBO:GO_0032571``.
        """
        prefix, identifier = self.parse_curie(curie)
        return self.expand_pair(prefix, identifier)

    def expand_all(self, curie: str) -> Optional[Collection[str]]:
        """Expand a CURIE pair to all possible URIs.

        :param curie:
            A string representing a compact URI
        :returns:
            A list of URIs that this converter can create for the given CURIE. The
            first entry is the "standard" URI then others are based on URI prefix
            synonyms. If the prefix is not registered to this converter, none is
            returned.

        >>> priority_prefix_map = {
        ...     "CHEBI": [
        ...         "http://purl.obolibrary.org/obo/CHEBI_",
        ...         "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:",
        ...     ],
        ... }
        >>> converter = Converter.from_priority_prefix_map(priority_prefix_map)
        >>> converter.expand_all("CHEBI:138488")
        ['http://purl.obolibrary.org/obo/CHEBI_138488', 'https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:138488']
        >>> converter.expand_all("NOPE:NOPE") is None
        True
        """
        prefix, identifier = self.parse_curie(curie)
        return self.expand_pair_all(prefix, identifier)

    def parse_curie(self, curie: str) -> ReferenceTuple:
        """Parse a CURIE."""
        reference = Reference.from_curie(curie, sep=self.delimiter)
        return reference.pair

    def expand_pair(self, prefix: str, identifier: str) -> Optional[str]:
        """Expand a CURIE pair to the standard URI.

        :param prefix:
            The prefix of the CURIE
        :param identifier:
            The local unique identifier of the CURIE
        :returns:
            A URI if this converter contains a URI prefix for the prefix in this CURIE

        >>> from curies import Converter
        >>> converter = Converter.from_prefix_map({
        ...    "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        ...    "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
        ...    "GO": "http://purl.obolibrary.org/obo/GO_",
        ... })
        >>> converter.expand_pair("CHEBI", "138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'
        >>> converter.expand_pair("missing", "0000000")
        """
        uri_prefix = self.prefix_map.get(prefix)
        if uri_prefix is None:
            return None
        return uri_prefix + identifier

    def expand_pair_all(self, prefix: str, identifier: str) -> Optional[Collection[str]]:
        """Expand a CURIE pair to all possible URIs.

        :param prefix:
            The prefix of the CURIE
        :param identifier:
            The local unique identifier of the CURIE
        :returns:
            A list of URIs that this converter can create for the given CURIE. The
            first entry is the "standard" URI then others are based on URI prefix
            synonyms. If the prefix is not registered to this converter, none is
            returned.

        >>> priority_prefix_map = {
        ...     "CHEBI": [
        ...         "http://purl.obolibrary.org/obo/CHEBI_",
        ...         "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:",
        ...     ],
        ... }
        >>> converter = Converter.from_priority_prefix_map(priority_prefix_map)
        >>> converter.expand_pair_all("CHEBI", "138488")
        ['http://purl.obolibrary.org/obo/CHEBI_138488', 'https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:138488']
        >>> converter.expand_pair_all("NOPE", "NOPE") is None
        True
        """
        record = self.get_record(prefix)
        if record is None:
            return None
        rv = [record.uri_prefix + identifier]
        for uri_prefix_synonyms in record.uri_prefix_synonyms:
            rv.append(uri_prefix_synonyms + identifier)
        return rv

    def standardize_prefix(self, prefix: str) -> Optional[str]:
        """Standardize a prefix.

        :param prefix:
            The prefix of the CURIE
        :returns:
            The standardized version of this prefix wrt this converter.
            If the prefix is not registered in this converter, returns none.

        >>> from curies import Converter, Record
        >>> converter = Converter.from_extended_prefix_map([
        ...     Record(prefix="CHEBI", prefix_synonyms=["chebi"], uri_prefix="..."),
        ... ])
        >>> converter.standardize_prefix("chebi")
        'CHEBI'
        >>> converter.standardize_prefix("CHEBI")
        'CHEBI'
        >>> converter.standardize_prefix("NOPE") is None
        True
        """
        return self.synonym_to_prefix.get(prefix)

    def standardize_curie(self, curie: str) -> Optional[str]:
        """Standardize a CURIE.

        :param curie:
            A string representing a compact URI
        :returns:
            A standardized version of the CURIE in case a prefix synonym was used.
            Note that this function is idempotent, i.e., if you give an already
            standard CURIE, it will just return it as is. If the CURIE can't be parsed
            with respect to the records in the converter, None is returned.

        >>> from curies import Converter, Record
        >>> converter = Converter.from_extended_prefix_map([
        ...     Record(prefix="CHEBI", prefix_synonyms=["chebi"], uri_prefix="http://purl.obolibrary.org/obo/CHEBI_"),
        ... ])
        >>> converter.standardize_curie("chebi:138488")
        'CHEBI:138488'
        >>> converter.standardize_curie("CHEBI:138488")
        'CHEBI:138488'
        >>> converter.standardize_curie("NOPE:NOPE") is None
        True
        """
        prefix, identifier = self.parse_curie(curie)
        norm_prefix = self.standardize_prefix(prefix)
        if norm_prefix is None:
            return None
        return self.format_curie(norm_prefix, identifier)

    def standardize_uri(self, uri: str) -> Optional[str]:
        """Standardize a URI.

        :param uri:
            A string representing a valid uniform resource identifier (URI)
        :returns:
            A standardized version of the URI in case a URI prefix synonym was used.
            Note that this function is idempotent, i.e., if you give an already
            standard URI, it will just return it as is. If the URI can't be parsed
            with respect to the records in the converter, None is returned.

        >>> from curies import Converter, Record
        >>> converter = Converter.from_extended_prefix_map([
        ...     Record(
        ...         prefix="CHEBI",
        ...         uri_prefix="http://purl.obolibrary.org/obo/CHEBI_",
        ...         uri_prefix_synonyms=[
        ...             "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:",
        ...         ],
        ...     ),
        ... ])
        >>> converter.standardize_uri("https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'
        >>> converter.standardize_uri("http://purl.obolibrary.org/obo/CHEBI_138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'
        >>> converter.standardize_uri("NOPE") is None
        True
        """
        prefix, identifier = self.parse_uri(uri)
        if prefix is None or identifier is None:
            return None
        # prefix is ensured to be in self.prefix_map because of successful parse
        return self.prefix_map[prefix] + identifier

    def pd_compress(
        self,
        df: "pandas.DataFrame",
        column: Union[str, int],
        target_column: Union[None, str, int] = None,
    ) -> None:
        """Convert all URIs in the given column to CURIEs.

        :param df: A pandas DataFrame
        :param column: The column in the dataframe containing URIs to convert to CURIEs.
        :param target_column: The column to put the results in. Defaults to input column.
        """
        df[column if target_column is None else target_column] = df[column].map(self.compress)

    def pd_expand(
        self,
        df: "pandas.DataFrame",
        column: Union[str, int],
        target_column: Union[None, str, int] = None,
    ) -> None:
        """Convert all CURIEs in the given column to URIs.

        :param df: A pandas DataFrame
        :param column: The column in the dataframe containing CURIEs to convert to URIs.
        :param target_column: The column to put the results in. Defaults to input column.
        """
        df[column if target_column is None else target_column] = df[column].map(self.expand)

    def pd_standardize_prefix(
        self,
        df: "pandas.DataFrame",
        *,
        column: Union[str, int],
        target_column: Union[None, str, int] = None,
    ) -> None:
        """Standardize all prefixes in the given column.

        :param df: A pandas DataFrame
        :param column: The column in the dataframe containing prefixes to standardize.
        :param target_column: The column to put the results in. Defaults to input column.
        """
        df[column if target_column is None else target_column] = df[column].map(
            self.standardize_prefix
        )

    def pd_standardize_curie(
        self,
        df: "pandas.DataFrame",
        *,
        column: Union[str, int],
        target_column: Union[None, str, int] = None,
    ) -> None:
        """Standardize all CURIEs in the given column.

        :param df: A pandas DataFrame
        :param column: The column in the dataframe containing CURIEs to standardize.
        :param target_column: The column to put the results in. Defaults to input column.
        """
        df[column if target_column is None else target_column] = df[column].map(
            self.standardize_curie
        )

    def pd_standardize_uri(
        self,
        df: "pandas.DataFrame",
        *,
        column: Union[str, int],
        target_column: Union[None, str, int] = None,
    ) -> None:
        """Standardize all URIs in the given column.

        :param df: A pandas DataFrame
        :param column: The column in the dataframe containing URIs to standardize.
        :param target_column: The column to put the results in. Defaults to input column.
        """
        df[column if target_column is None else target_column] = df[column].map(
            self.standardize_uri
        )

    def file_compress(
        self, path: Union[str, Path], column: int, sep: Optional[str] = None, header: bool = True
    ) -> None:
        """Convert all URIs in the given column of a CSV file to CURIEs.

        :param path: A pandas DataFrame
        :param column: The column in the dataframe containing URIs to convert to CURIEs.
        :param sep: The delimiter of the CSV file, defaults to tab
        :param header: Does the file have a header row?
        """
        self._file_helper(self.compress, path=path, column=column, sep=sep, header=header)

    def file_expand(
        self, path: Union[str, Path], column: int, sep: Optional[str] = None, header: bool = True
    ) -> None:
        """Convert all CURIEs in the given column of a CSV file to URIs.

        :param path: A pandas DataFrame
        :param column: The column in the dataframe containing CURIEs to convert to URIs.
        :param sep: The delimiter of the CSV file, defaults to tab
        :param header: Does the file have a header row?
        """
        self._file_helper(self.expand, path=path, column=column, sep=sep, header=header)

    @staticmethod
    def _file_helper(
        func: Callable[[str], Optional[str]],
        path: Union[str, Path],
        column: int,
        sep: Optional[str] = None,
        header: bool = True,
    ) -> None:
        path = Path(path).expanduser().resolve()
        rows = []
        delimiter = sep or "\t"
        with path.open() as file_in:
            reader = csv.reader(file_in, delimiter=delimiter)
            _header = next(reader) if header else None
            for row in reader:
                row[column] = func(row[column]) or ""
                rows.append(row)
        with path.open("w") as file_out:
            writer = csv.writer(file_out, delimiter=delimiter)
            if _header:
                writer.writerow(_header)
            writer.writerows(rows)

    def get_record(self, prefix: str) -> Optional[Record]:
        """Get the record for the prefix."""
        # TODO better data structure for this
        for record in self.records:
            if record.prefix == prefix:
                return record
        return None


def _f(x: str) -> str:
    return x


def chain(converters: Sequence[Converter], case_sensitive: bool = True) -> Converter:
    """Chain several converters.

    :param converters: A list or tuple of converters
    :param case_sensitive: If false, will not allow case-sensitive duplicates
    :returns:
        A converter that looks up one at a time in the other converters.
    :raises ValueError:
        If there are no converters
    """
    if not converters:
        raise ValueError

    norm_func: Callable[[str], str]
    if case_sensitive:
        norm_func = _f
    else:
        norm_func = str.casefold

    key_to_pair: Dict[str, Tuple[str, str]] = {}
    #: A mapping from the canonical key to the secondary URI expansions
    uri_prefix_tails: DefaultDict[str, Set[str]] = defaultdict(set)
    #: A mapping from the canonical key to the secondary prefixes
    prefix_tails: DefaultDict[str, Set[str]] = defaultdict(set)
    for converter in converters:
        for record in converter.records:
            key = norm_func(record.prefix)
            if key not in key_to_pair:
                key_to_pair[key] = record.prefix, record.uri_prefix
                uri_prefix_tails[key].update(record.uri_prefix_synonyms)
                prefix_tails[key].update(record.prefix_synonyms)
            else:
                uri_prefix_tails[key].add(record.uri_prefix)
                uri_prefix_tails[key].update(record.uri_prefix_synonyms)
                prefix_tails[key].add(record.prefix)
                prefix_tails[key].update(record.prefix_synonyms)

    # clean up potential duplicates from merging
    for key, uri_prefixes in uri_prefix_tails.items():
        uri_prefix = key_to_pair[key][1]
        if uri_prefix in uri_prefixes:
            uri_prefixes.remove(uri_prefix)
    for key, prefixes in prefix_tails.items():
        prefix = key_to_pair[key][0]
        if prefix in prefixes:
            prefixes.remove(prefix)

    return Converter(
        [
            Record(
                prefix=prefix,
                uri_prefix=uri_prefix,
                prefix_synonyms=sorted(prefix_tails[key]),
                uri_prefix_synonyms=sorted(uri_prefix_tails[key]),
            )
            for key, (prefix, uri_prefix) in key_to_pair.items()
        ]
    )
