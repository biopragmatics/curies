# -*- coding: utf-8 -*-

"""Data structures and algorithms for :mod:`curies`."""

import csv
import itertools as itt
import json
import logging
from collections import defaultdict
from functools import partial
from pathlib import Path
from textwrap import dedent
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Collection,
    DefaultDict,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
    overload,
)

import requests
from pydantic import BaseModel, Field
from pytrie import StringTrie

from ._pydantic_compat import PYDANTIC_V1, field_validator, get_field_validator_values

if not PYDANTIC_V1:
    from pydantic import ConfigDict

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
    # Utilities
    "chain",
    "upgrade_prefix_map",
    # Loaders
    "load_extended_prefix_map",
    "load_prefix_map",
    "load_jsonld_context",
    "load_shacl",
    # Writers
    "write_extended_prefix_map",
    "write_jsonld_context",
    "write_shacl",
    "write_tsv",
]

logger = logging.getLogger(__name__)

X = TypeVar("X")
LocationOr = Union[str, Path, X]


class ReferenceTuple(NamedTuple):
    """A pair of a prefix (corresponding to a semantic space) and a local unique identifier in that semantic space.

    This class derives from the "named tuple" which means that it acts
    like a tuple in most senses - it can be hashed and unpacked
    like most other tuples. Underneath, it has a C implementation
    and is very efficient.

    A reference tuple can be constructed two ways:

    >>> ReferenceTuple("chebi", "1234")
    ReferenceTuple(prefix='chebi', identifier='1234')

    >>> ReferenceTuple.from_curie("chebi:1234")
    ReferenceTuple(prefix='chebi', identifier='1234')

    A reference tuple can be formatted as a CURIE string with
    the ``curie`` attribute

    >>> ReferenceTuple.from_curie("chebi:1234").curie
    'chebi:1234'

    Reference tuples can be sliced like regular 2-tuples

    >>> t = ReferenceTuple.from_curie("chebi:1234")
    >>> t[0]
    'chebi'
    >>> t[1]
    '1234'

    Similarly, reference tuples can be unpacked like regular 2-tuples

    >>> prefix, identifier = ReferenceTuple.from_curie("chebi:1234")
    >>> prefix
    'chebi'
    >>> identifier
    '1234'

    Because they are named tuples, reference tuples can be accessed
    with attributes

    >>> t = ReferenceTuple.from_curie("chebi:1234")
    >>> t.prefix
    'chebi'
    >>> t.identifier
    '1234'
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

    A reference can be constructed several ways:

    >>> Reference(prefix="chebi", identifier="1234")
    Reference(prefix='chebi', identifier='1234')

    >>> Reference.from_curie("chebi:1234")
    Reference(prefix='chebi', identifier='1234')

    A reference can also be constructued using Pydantic's parsing utilities,
    but keep in mind if you're using Pydantic v1 or Pydantic v2.

    A reference can be formatted as a CURIE string with
    the ``curie`` attribute

    >>> Reference.from_curie("chebi:1234").curie
    'chebi:1234'

    References can't be sliced like reference tuples, but they can still
    be accessed through attributes

    >>> t = Reference.from_curie("chebi:1234")
    >>> t.prefix
    'chebi'
    >>> t.identifier
    '1234'

    If you need a performance gain, you can get a :class:`ReferenceTuple`
    using the ``pair`` attribute:

    >>> reference = Reference.from_curie("chebi:1234")
    >>> reference.pair
    ReferenceTuple(prefix='chebi', identifier='1234')
    """

    prefix: str = Field(
        ...,
        description="The prefix used in a compact URI (CURIE).",
    )
    identifier: str = Field(
        ..., description="The local unique identifier used in a compact URI (CURIE)."
    )

    if PYDANTIC_V1:

        class Config:
            """Pydantic configuration for references."""

            frozen = True

    else:
        model_config = ConfigDict(frozen=True)

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


RecordKey = Tuple[str, str, str, str]


class Record(BaseModel):  # type:ignore
    """A record of some prefixes and their associated URI prefixes.

    A list of records can be annotated in a FastAPI setting with the following:

    .. code-block:: python

        from typing import List
        from curies import Record
        from pydantic import BaseModel

        class Records(BaseModel):
            __root__ = List[Record]

    .. seealso:: https://github.com/cthoyt/curies/issues/70
    """

    prefix: str = Field(..., description="The canonical prefix, used in the reverse prefix map")
    uri_prefix: str = Field(
        ..., description="The canonical URI prefix, used in the forward prefix map"
    )
    prefix_synonyms: List[str] = Field(default_factory=list)
    uri_prefix_synonyms: List[str] = Field(default_factory=list)
    pattern: Optional[str] = Field(
        default=None,
        description="The regular expression pattern for entries in this semantic space. "
        "Warning: this is an experimental feature.",
    )

    @field_validator("prefix_synonyms")  # type:ignore
    def prefix_not_in_synonyms(cls, v: str, values: Mapping[str, Any]) -> str:  # noqa:N805
        """Check that the canonical prefix does not apper in the prefix synonym list."""
        prefix = get_field_validator_values(values, "prefix")
        if prefix in v:
            raise ValueError(f"Duplicate of canonical prefix `{prefix}` in prefix synonyms")
        return v

    @field_validator("uri_prefix_synonyms")  # type:ignore
    def uri_prefix_not_in_synonyms(cls, v: str, values: Mapping[str, Any]) -> str:  # noqa:N805
        """Check that the canonical URI prefix does not apper in the URI prefix synonym list."""
        uri_prefix = get_field_validator_values(values, "uri_prefix")
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

    @property
    def _key(self) -> RecordKey:
        """Get a hashable key."""
        return (
            self.prefix,
            self.uri_prefix,
            ",".join(sorted(self.prefix_synonyms)),
            ",".join(sorted(self.uri_prefix_synonyms)),
        )


class DuplicateSummary(NamedTuple):
    """A triple representing two records that are duplicated, either based on a CURIE or URI prefix."""

    record_1: Record
    record_2: Record
    prefix: str


class DuplicateValueError(ValueError):
    """An error raised with constructing a converter with data containing duplicate values."""

    def __init__(self, duplicates: List[DuplicateSummary]) -> None:
        """Initialize the error."""
        self.duplicates = duplicates

    def _str(self) -> str:
        rv = ""
        for duplicate in self.duplicates:
            rv += f"\n{duplicate.prefix}:\n\t{duplicate.record_1}\n\t{duplicate.record_2}\n"
        return rv


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


class StandardizationError(ValueError):
    """An error raised on standardization."""


class PrefixStandardizationError(StandardizationError):
    """An error raise when a prefix can't be standardized."""


class CURIEStandardizationError(StandardizationError):
    """An error raise when a CURIE can't be standardized."""


class URIStandardizationError(StandardizationError):
    """An error raise when a URI can't be standardized."""


def _get_duplicate_uri_prefixes(records: List[Record]) -> List[DuplicateSummary]:
    return [
        DuplicateSummary(record_1, record_2, uri_prefix)
        for record_1, record_2 in itt.combinations(records, 2)
        for uri_prefix, up2 in itt.product(record_1._all_uri_prefixes, record_2._all_uri_prefixes)
        if uri_prefix == up2
    ]


def _get_duplicate_prefixes(records: List[Record]) -> List[DuplicateSummary]:
    return [
        DuplicateSummary(record_1, record_2, prefix)
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


def _get_pattern_map(records: List[Record]) -> Dict[str, str]:
    return {record.prefix: record.pattern for record in records if record.pattern}


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
    #: A mapping from prefix to regular expression pattern. Not necessarily complete wrt the prefix map.
    #:
    #: .. warning:: patterns are an experimental feature
    pattern_map: Dict[str, str]

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
        self.records = sorted(records, key=lambda r: r.prefix)
        self.prefix_map = _get_prefix_map(records)
        self.synonym_to_prefix = _get_prefix_synmap(records)
        self.reverse_prefix_map = _get_reverse_prefix_map(records)
        self.trie = StringTrie(self.reverse_prefix_map)
        self.pattern_map = _get_pattern_map(records)

    @property
    def bimap(self) -> Mapping[str, str]:
        """Get the bijective mapping between CURIE prefixes and URI prefixes."""
        return {r.prefix: r.uri_prefix for r in self.records}

    def _match_record(
        self, external: Record, case_sensitive: bool = True
    ) -> Mapping[RecordKey, List[str]]:
        """Match the given record to existing records."""
        rv: DefaultDict[RecordKey, List[str]] = defaultdict(list)
        for record in self.records:
            # Match CURIE prefixes
            if _eq(external.prefix, record.prefix, case_sensitive=case_sensitive):
                rv[record._key].append("prefix match")
            if _in(external.prefix, record.prefix_synonyms, case_sensitive=case_sensitive):
                rv[record._key].append("prefix match")
            for prefix_synonym in external.prefix_synonyms:
                if _eq(prefix_synonym, record.prefix, case_sensitive=case_sensitive):
                    rv[record._key].append("prefix match")
                if _in(prefix_synonym, record.prefix_synonyms, case_sensitive=case_sensitive):
                    rv[record._key].append("prefix match")

            # Match URI prefixes
            if _eq(external.uri_prefix, record.uri_prefix, case_sensitive=case_sensitive):
                rv[record._key].append("URI prefix match")
            if _in(external.uri_prefix, record.uri_prefix_synonyms, case_sensitive=case_sensitive):
                rv[record._key].append("URI prefix match")
            for uri_prefix_synonym in external.uri_prefix_synonyms:
                if _eq(uri_prefix_synonym, record.uri_prefix, case_sensitive=case_sensitive):
                    rv[record._key].append("URI prefix match")
                if _in(
                    uri_prefix_synonym, record.uri_prefix_synonyms, case_sensitive=case_sensitive
                ):
                    rv[record._key].append("URI prefix match")
        return dict(rv)

    def add_record(self, record: Record, case_sensitive: bool = True, merge: bool = False) -> None:
        """Append a record to the converter."""
        matched = self._match_record(record, case_sensitive=case_sensitive)
        if len(matched) > 1:
            raise ValueError(f"new record has duplicates: {matched}")
        if len(matched) == 1:
            if not merge:
                raise ValueError(f"new record already exists and merge=False: {matched}")

            key = list(matched)[0]
            existing_record = next(r for r in self.records if r._key == key)
            self._merge(record, into=existing_record)
            self._index(existing_record)
        else:
            # Append a new record
            self.records.append(record)
            self._index(record)

    @staticmethod
    def _merge(record: Record, into: Record) -> None:
        for prefix_synonym in itt.chain([record.prefix], record.prefix_synonyms):
            if prefix_synonym not in into._all_prefixes:
                into.prefix_synonyms.append(prefix_synonym)
        into.prefix_synonyms.sort()

        for uri_prefix_synonym in itt.chain([record.uri_prefix], record.uri_prefix_synonyms):
            if uri_prefix_synonym not in into._all_uri_prefixes:
                into.uri_prefix_synonyms.append(uri_prefix_synonym)
        into.uri_prefix_synonyms.sort()

    def _index(self, record: Record) -> None:
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

        if record.pattern and record.prefix not in self.pattern_map:
            self.pattern_map[record.prefix] = record.pattern

    def add_prefix(
        self,
        prefix: str,
        uri_prefix: str,
        prefix_synonyms: Optional[Collection[str]] = None,
        uri_prefix_synonyms: Optional[Collection[str]] = None,
        *,
        case_sensitive: bool = True,
        merge: bool = False,
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
        :param case_sensitive:
            Should prefixes and URI prefixes be compared in a case-sensitive manner when checking
            for uniqueness? Defaults to True.
        :param merge:
            Should this record be merged into an existing record if it uniquely maps to a single
            existing record? When false, will raise an error if one or more existing records can
            be mapped. Defaults to false.

        This can be used to add missing namespaces on-the-fly to an existing converter:

        >>> import curies
        >>> converter = curies.get_obo_converter()
        >>> converter.add_prefix("hgnc", "https://bioregistry.io/hgnc:")
        >>> converter.expand("hgnc:1234")
        'https://bioregistry.io/hgnc:1234'
        >>> converter.expand("GO:0032571")
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
        self.add_record(record, case_sensitive=case_sensitive, merge=merge)

    @classmethod
    def from_extended_prefix_map(
        cls, records: LocationOr[Iterable[Union[Record, Dict[str, Any]]]], **kwargs: Any
    ) -> "Converter":
        """Get a converter from a list of dictionaries by creating records out of them.

        :param records:
             One of the following:

            - An iterable of :class:`curies.Record` objects or dictionaries that will
              get converted into record objects that together constitute an extended prefix map
            - A string containing a remote location of a JSON file containg an extended prefix map
            - A string or :class:`pathlib.Path` object corresponding to a local file path to a JSON file
              containing an extended prefix map
        :param kwargs: Keyword arguments to pass to :meth:`curies.Converter.__init__`
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

        Expand using the preferred/canonical prefix:

        >>> converter.expand("CHEBI:138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'

        Expand using a prefix synonym:

        >>> converter.expand("chebi:138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'

        Compress using the preferred/canonical URI prefix:

        >>> converter.compress("http://purl.obolibrary.org/obo/CHEBI_138488")
        'CHEBI:138488'

        Compressing using a URI prefix synonym:

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
            One of the following:

            - A mapping whose keys represent CURIE prefixes and values represent URI prefixes
            - A string containing a remote location of a JSON file containg a prefix map
            - A string or :class:`pathlib.Path` object corresponding to a local file path to a JSON file
              containing a prefix map
        :param kwargs: Keyword arguments to pass to :meth:`curies.Converter.__init__`
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
        cls, reverse_prefix_map: LocationOr[Mapping[str, str]], **kwargs: Any
    ) -> "Converter":
        """Get a converter from a reverse prefix map.

        :param reverse_prefix_map:
            A mapping whose keys are URI prefixes and whose values are the corresponding prefixes.
            This data structure allow for multiple different URI formats to point to the same
            prefix.
        :param kwargs: Keyword arguments to pass to :meth:`curies.Converter.__init__`
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
        >>> "chebi" in converter.prefix_map
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
        return cls(records, **kwargs)

    @classmethod
    def from_jsonld(cls, data: LocationOr[Dict[str, Any]], **kwargs: Any) -> "Converter":
        """Get a converter from a JSON-LD object, which contains a prefix map in its ``@context`` key.

        :param data:
            A JSON-LD object
        :param kwargs: Keyword arguments to pass to :meth:`curies.Converter.__init__`
        :return: A converter

        Example from a remote context file:

        >>> base = "https://raw.githubusercontent.com"
        >>> url = f"{base}/biopragmatics/bioregistry/main/exports/contexts/semweb.context.jsonld"
        >>> converter = Converter.from_jsonld(url)
        >>> "rdf" in converter.prefix_map

        .. seealso:: https://www.w3.org/TR/json-ld11/#the-context defines the ``@context`` aspect of JSON-LD
        """
        prefix_map = {}
        for key, value in _prepare(data)["@context"].items():
            # TODO how to handle key == "@base"?
            if not key:
                logger.warning(
                    "The JSON-LD specification says in https://www.w3.org/TR/json-ld/#terms that "
                    "keys are not allowed to be empty strings. The given @context object contained "
                    "an empty string as one of its keys"
                )
                continue
            if key.startswith("@"):
                continue
            if isinstance(value, str):
                prefix_map[key] = value
            elif isinstance(value, dict) and value.get("@prefix") is True:
                prefix_map[key] = value["@id"]
        return cls.from_prefix_map(prefix_map, **kwargs)

    @classmethod
    def from_jsonld_github(
        cls, owner: str, repo: str, *path: str, branch: str = "main", **kwargs: Any
    ) -> "Converter":
        """Construct a remote JSON-LD URL on GitHub then parse with :meth:`Converter.from_jsonld`.

        :param owner: A github repository owner or organization (e.g., ``biopragmatics``)
        :param repo: The name of the repository (e.g., ``bioregistry``)
        :param path: The file path in the GitHub repository to a JSON-LD context file.
        :param branch: The branch from which the file should be downloaded. Defaults to ``main``, for old
            repositories this might need to be changed to ``master``.
        :param kwargs: Keyword arguments to pass to :meth:`curies.Converter.__init__`
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
        return cls.from_jsonld(url, **kwargs)

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

    @classmethod
    def from_shacl(
        cls,
        graph: Union[str, Path, "rdflib.Graph"],
        format: Optional[str] = None,
        **kwargs: Any,
    ) -> "Converter":
        """Get a converter from SHACL, either in a turtle f.

        :param graph: A RDFLib graph, a Path, a string representing a file path, or a string URL
        :param format: The RDF format, if a file path is given
        :param kwargs: Keyword arguments to pass to :meth:`Converter.__init__`
        :return: A converter
        """
        if isinstance(graph, (str, Path)):
            import rdflib

            temporary_graph = rdflib.Graph()
            temporary_graph.parse(location=graph, format=format)
            graph = temporary_graph

        query = """\
            SELECT ?curie_prefix ?uri_prefix ?pattern
            WHERE {
                ?bnode1 sh:declare ?bnode2 .
                ?bnode2 sh:prefix ?curie_prefix .
                ?bnode2 sh:namespace ?uri_prefix .
                OPTIONAL { ?bnode2 sh:pattern ?pattern . }
            }
        """
        results = graph.query(query)
        records = [
            Record(prefix=str(prefix), uri_prefix=str(uri_prefix), pattern=pattern and str(pattern))
            for prefix, uri_prefix, pattern in results
        ]
        return cls(records, **kwargs)

    def get_prefixes(self, *, include_synonyms: bool = False) -> Set[str]:
        """Get the set of prefixes covered by this converter.

        :param include_synonyms: If true, include secondary prefixes.
        :return:
            A set of primary prefixes covered by the converter. If ``include_synonyms`` is
            set to ``True``, secondary prefixes (i.e., ones in :data:`Record.prefix_synonyms`
            are also included
        """
        rv = {record.prefix for record in self.records}
        if include_synonyms:
            rv.update(
                prefix_synonym
                for record in self.records
                for prefix_synonym in record.prefix_synonyms
            )
        return rv

    def get_uri_prefixes(self, *, include_synonyms: bool = False) -> Set[str]:
        """Get the set of URI prefixes covered by this converter.

        :param include_synonyms: If true, include secondary prefixes.
        :return:
            A set of primary URI prefixes covered by the converter. If ``include_synonyms`` is
            set to ``True``, secondary URI prefixes (i.e., ones in :data:`Record.uri_prefix_synonyms`
            are also included
        """
        rv = {record.uri_prefix for record in self.records}
        if include_synonyms:
            rv.update(
                uri_prefix_synonym
                for record in self.records
                for uri_prefix_synonym in record.uri_prefix_synonyms
            )
        return rv

    def format_curie(self, prefix: str, identifier: str) -> str:
        """Format a prefix and identifier into a CURIE string."""
        return f"{prefix}{self.delimiter}{identifier}"

    def is_uri(self, s: str) -> bool:
        """Check if the string can be parsed as a URI by this converter.

        :param s: A string that might be a URI
        :returns: If the string can be parsed as a URI by this converter.
            Note that some valid URIs, when passed to this function, will
            result in False if their URI prefixes are not registered with this
            converter.

        >>> import curies
        >>> converter = curies.get_obo_converter()
        >>> converter.is_uri("http://purl.obolibrary.org/obo/GO_1234567")
        True
        >>> converter.is_uri("GO:1234567")
        False

        The following is a valid URI, but the prefix is not registered
        with the converter based on the OBO Foundry prefix map, so it returns
        False.

        >>> converter.is_uri("http://proteopedia.org/wiki/index.php/2gc4")
        False
        """
        return self.compress(s) is not None

    # docstr-coverage:excused `overload`
    @overload
    def compress_or_standardize(
        self, uri_or_curie: str, *, strict: Literal[True] = True, passthrough: bool = ...
    ) -> str: ...

    # docstr-coverage:excused `overload`
    @overload
    def compress_or_standardize(
        self,
        uri_or_curie: str,
        *,
        strict: Literal[False] = False,
        passthrough: Literal[True] = True,
    ) -> str: ...

    # docstr-coverage:excused `overload`
    @overload
    def compress_or_standardize(
        self,
        uri_or_curie: str,
        *,
        strict: Literal[False] = False,
        passthrough: Literal[False] = False,
    ) -> Optional[str]: ...

    def compress_or_standardize(
        self, uri_or_curie: str, *, strict: bool = False, passthrough: bool = False
    ) -> Optional[str]:
        """Compress a URI or standardize a CURIE.

        :param uri_or_curie:
            A string representing a compact URI (CURIE) or a URI.
        :param strict: If true and the string is neither a URI that can be compressed nor a CURIE that can be
            standardized, returns an error. Defaults to false.
        :param passthrough: If true, strict is false, and the string is neither a URI that can be compressed
            nor a CURIE that can be standardized, return the input. Defaults to false.
        :returns:
            If the string is a URI, and it can be compressed, returns the corresponding CURIE.
            If the string is a CURIE, and it can be standardized, returns the standard CURIE.
        :raises CompressionError:
            If strict is true and the URI can't be compressed

        >>> from curies import Converter, Record
        >>> converter = Converter.from_extended_prefix_map([
        ...     Record(
        ...          prefix="CHEBI",
        ...          prefix_synonyms=["chebi"],
        ...          uri_prefix="http://purl.obolibrary.org/obo/CHEBI_",
        ...          uri_prefix_synonyms=["https://identifiers.org/chebi:"],
        ...     ),
        ... ])
        >>> converter.compress_or_standardize("http://purl.obolibrary.org/obo/CHEBI_138488")
        'CHEBI:138488'
        >>> converter.compress_or_standardize("https://identifiers.org/chebi:138488")
        'CHEBI:138488'

        >>> converter.compress_or_standardize("CHEBI:138488")
        'CHEBI:138488'
        >>> converter.compress_or_standardize("chebi:138488")
        'CHEBI:138488'

        >>> converter.compress_or_standardize("missing:0000000")
        >>> converter.compress_or_standardize("https://example.com/missing:0000000")
        """
        if self.is_uri(uri_or_curie):
            return self.compress(uri_or_curie, strict=True)
        if self.is_curie(uri_or_curie):
            return self.standardize_curie(uri_or_curie, strict=True)
        if strict:
            raise CompressionError(uri_or_curie)
        if passthrough:
            return uri_or_curie
        return None

    def compress_strict(self, uri: str) -> str:
        """Compress a URI to a CURIE, and raise an error of not possible."""
        return self.compress(uri, strict=True)

    # docstr-coverage:excused `overload`
    @overload
    def compress(
        self, uri: str, *, strict: Literal[True] = True, passthrough: bool = ...
    ) -> str: ...

    # docstr-coverage:excused `overload`
    @overload
    def compress(
        self, uri: str, *, strict: Literal[False] = False, passthrough: Literal[True] = True
    ) -> str: ...

    # docstr-coverage:excused `overload`
    @overload
    def compress(
        self, uri: str, *, strict: Literal[False] = False, passthrough: Literal[False] = False
    ) -> Optional[str]: ...

    def compress(
        self, uri: str, *, strict: bool = False, passthrough: bool = False
    ) -> Optional[str]:
        """Compress a URI to a CURIE, if possible.

        :param uri:
            A string representing a valid uniform resource identifier (URI)
        :param strict: If true and the URI can't be compressed, returns an error. Defaults to false.
        :param passthrough: If true, strict is false, and the URI can't be compressed, return the input.
            Defaults to false.
        :returns:
            A compact URI if this converter could find an appropriate URI prefix, otherwise none.
        :raises CompressionError:
            If strict is set to true and the URI can't be compressed

        >>> from curies import Converter
        >>> converter = Converter.from_prefix_map({
        ...    "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        ...    "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
        ...    "GO": "http://purl.obolibrary.org/obo/GO_",
        ...    "OBO": "http://purl.obolibrary.org/obo/",
        ... })
        >>> converter.compress("http://purl.obolibrary.org/obo/GO_0032571")
        'GO:0032571'
        >>> converter.compress("http://purl.obolibrary.org/obo/go.owl")
        'OBO:go.owl'
        >>> converter.compress("http://example.org/missing:0000000")

        .. note::

            If there are partially overlapping *URI prefixes* in this converter
            (e.g., ``http://purl.obolibrary.org/obo/GO_`` for the prefix ``GO`` and
            ``http://purl.obolibrary.org/obo/`` for the prefix ``OBO``), the longest
            URI prefix will always be matched. For example, parsing
            ``http://purl.obolibrary.org/obo/GO_0032571`` will return ``GO:0032571``
            instead of ``OBO:GO_0032571``.
        """
        prefix, identifier = self.parse_uri(uri)
        if prefix and identifier:
            return self.format_curie(prefix, identifier)
        if strict:
            raise CompressionError(uri)
        if passthrough:
            return uri
        return None

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
        ReferenceTuple(prefix='CHEBI', identifier='138488')
        >>> converter.parse_uri("http://example.org/missing:0000000")
        (None, None)
        """
        try:
            value, prefix = self.trie.longest_prefix_item(uri)
        except KeyError:
            return None, None
        else:
            return ReferenceTuple(prefix, uri[len(value) :])

    def is_curie(self, s: str) -> bool:
        """Check if the string can be parsed as a CURIE by this converter.

        :param s: A string that might be a CURIE
        :returns: If the string can be parsed as a CURIE by this converter.
            Note that some valid CURIEs, when passed to this function, will
            result in False if their prefixes are not registered with this
            converter.

        >>> import curies
        >>> converter = curies.get_obo_converter()
        >>> converter.is_curie("GO:1234567")
        True
        >>> converter.is_curie("http://purl.obolibrary.org/obo/GO_1234567")
        False

        The following is a valid CURIE, but the prefix is not registered
        with the converter based on the OBO Foundry prefix map, so it returns
        False.

        >>> converter.is_curie("pdb:2gc4")
        False
        """
        try:
            return self.expand(s) is not None
        except ValueError:
            return False

    # docstr-coverage:excused `overload`
    @overload
    def expand_or_standardize(
        self, curie_or_uri: str, *, strict: Literal[True] = True, passthrough: bool = ...
    ) -> str: ...

    # docstr-coverage:excused `overload`
    @overload
    def expand_or_standardize(
        self,
        curie_or_uri: str,
        *,
        strict: Literal[False] = False,
        passthrough: Literal[True] = True,
    ) -> str: ...

    # docstr-coverage:excused `overload`
    @overload
    def expand_or_standardize(
        self,
        curie_or_uri: str,
        *,
        strict: Literal[False] = False,
        passthrough: Literal[False] = False,
    ) -> Optional[str]: ...

    def expand_or_standardize(
        self, curie_or_uri: str, *, strict: bool = False, passthrough: bool = False
    ) -> Optional[str]:
        """Expand a CURIE or standardize a URI.

        :param curie_or_uri:
            A string representing a compact URI (CURIE) or a URI.
        :param strict: If true and the string is neither a CURIE that can be expanded nor a URI that can be
            standardized, returns an error. Defaults to false.
        :param passthrough: If true, strict is false, and the string is neither a CURIE that can be expanded
            nor a URI that can be standardized, return the input. Defaults to false.
        :returns:
            If the string is a CURIE, and it can be expanded, returns the corresponding URI.
            If the string is a URI, and it can be standardized, returns the standard URI.
        :raises ExpansionError:
            If strict is true and the CURIE can't be expanded

        >>> from curies import Converter, Record
        >>> converter = Converter.from_extended_prefix_map([
        ...     Record(
        ...          prefix="CHEBI",
        ...          prefix_synonyms=["chebi"],
        ...          uri_prefix="http://purl.obolibrary.org/obo/CHEBI_",
        ...          uri_prefix_synonyms=["https://identifiers.org/chebi:"],
        ...     ),
        ... ])
        >>> converter.expand_or_standardize("CHEBI:138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'
         >>> converter.expand_or_standardize("chebi:138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'

        >>> converter.expand_or_standardize("http://purl.obolibrary.org/obo/CHEBI_138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'
        >>> converter.expand_or_standardize("https://identifiers.org/chebi:138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'

        >>> converter.expand_or_standardize("missing:0000000")
        >>> converter.expand_or_standardize("https://example.com/missing:0000000")
        """
        if self.is_curie(curie_or_uri):
            return self.expand(curie_or_uri, strict=True)
        if self.is_uri(curie_or_uri):
            return self.standardize_uri(curie_or_uri, strict=True)
        if strict:
            raise ExpansionError(curie_or_uri)
        if passthrough:
            return curie_or_uri
        return None

    def expand_strict(self, curie: str) -> str:
        """Expand a CURIE to a URI, and raise an error of not possible."""
        return self.expand(curie, strict=True)

    # docstr-coverage:excused `overload`
    @overload
    def expand(
        self, curie: str, *, strict: Literal[True] = True, passthrough: bool = ...
    ) -> str: ...

    # docstr-coverage:excused `overload`
    @overload
    def expand(
        self, curie: str, *, strict: Literal[False] = False, passthrough: Literal[True] = True
    ) -> str: ...

    # docstr-coverage:excused `overload`
    @overload
    def expand(
        self, curie: str, *, strict: Literal[False] = False, passthrough: Literal[False] = False
    ) -> Optional[str]: ...

    def expand(
        self, curie: str, *, strict: bool = False, passthrough: bool = False
    ) -> Optional[str]:
        """Expand a CURIE to a URI, if possible.

        :param curie:
            A string representing a compact URI (CURIE)
        :param strict: If true and the CURIE can't be expanded, returns an error. Defaults to false.
        :param passthrough: If true, strict is false, and the CURIE can't be expanded, return the input.
            Defaults to false. If your strings can either be a CURIE _or_ a URI, consider using
            :meth:`Converter.expand_or_standardize` instead.
        :returns:
            A URI if this converter contains a URI prefix for the prefix in this CURIE
        :raises ExpansionError:
            If strict is true and the CURIE can't be expanded

        >>> from curies import Converter
        >>> converter = Converter.from_prefix_map({
        ...    "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        ...    "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
        ...    "GO": "http://purl.obolibrary.org/obo/GO_",
        ... })
        >>> converter.expand("CHEBI:138488")
        'http://purl.obolibrary.org/obo/CHEBI_138488'
        >>> converter.expand("missing:0000000")
        """
        prefix, identifier = self.parse_curie(curie)
        rv = self.expand_pair(prefix, identifier)
        if rv:
            return rv
        if strict:
            raise ExpansionError(curie)
        if passthrough:
            return curie
        return None

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

    # docstr-coverage:excused `overload`
    @overload
    def standardize_prefix(
        self, prefix: str, *, strict: Literal[True] = True, passthrough: bool = False
    ) -> str: ...

    # docstr-coverage:excused `overload`
    @overload
    def standardize_prefix(
        self, prefix: str, *, strict: Literal[False] = False, passthrough: Literal[True] = True
    ) -> str: ...

    # docstr-coverage:excused `overload`
    @overload
    def standardize_prefix(
        self, prefix: str, *, strict: Literal[False] = False, passthrough: Literal[False] = False
    ) -> Optional[str]: ...

    def standardize_prefix(
        self, prefix: str, *, strict: bool = False, passthrough: bool = False
    ) -> Optional[str]:
        """Standardize a prefix.

        :param prefix:
            The prefix of the CURIE
        :param strict: If true and the prefix can't be standardized, returns an error. Defaults to false.
        :param passthrough: If true, strict is false, and the prefix can't be standardized, return the input.
            Defaults to false.
        :returns:
            The standardized version of this prefix wrt this converter.
            If the prefix is not registered in this converter, returns none.
        :raises PrefixStandardizationError:
            If strict is true and the prefix can't be standardied

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
        >>> converter.standardize_prefix("NOPE", passthrough=True)
        'NOPE'
        """
        rv = self.synonym_to_prefix.get(prefix)
        if rv:
            return rv
        if strict:
            raise PrefixStandardizationError(prefix)
        if passthrough:
            return prefix
        return None

    # docstr-coverage:excused `overload`
    @overload
    def standardize_curie(
        self, curie: str, *, strict: Literal[True] = True, passthrough: bool = False
    ) -> str: ...

    # docstr-coverage:excused `overload`
    @overload
    def standardize_curie(
        self, curie: str, *, strict: Literal[False] = False, passthrough: Literal[True] = True
    ) -> str: ...

    # docstr-coverage:excused `overload`
    @overload
    def standardize_curie(
        self, curie: str, *, strict: Literal[False] = False, passthrough: Literal[False] = False
    ) -> Optional[str]: ...

    def standardize_curie(
        self, curie: str, *, strict: bool = False, passthrough: bool = False
    ) -> Optional[str]:
        """Standardize a CURIE.

        :param curie:
            A string representing a compact URI (CURIE)
        :param strict: If true and the CURIE can't be standardized, returns an error. Defaults to false.
        :param passthrough: If true, strict is false, and the CURIE can't be standardized, return the input.
            Defaults to false.
        :returns:
            A standardized version of the CURIE in case a prefix synonym was used.
            Note that this function is idempotent, i.e., if you give an already
            standard CURIE, it will just return it as is. If the CURIE can't be parsed
            with respect to the records in the converter, None is returned.
        :raises CURIEStandardizationError:
            If strict is true and the CURIE can't be standardized

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
        >>> converter.standardize_curie("NOPE:NOPE", passthrough=True)
        'NOPE:NOPE'
        """
        prefix, identifier = self.parse_curie(curie)
        norm_prefix = self.standardize_prefix(prefix)
        if norm_prefix is not None:
            return self.format_curie(norm_prefix, identifier)
        if strict:
            raise CURIEStandardizationError(curie)
        if passthrough:
            return curie
        return None

    # docstr-coverage:excused `overload`
    @overload
    def standardize_uri(
        self, uri: str, *, strict: Literal[True] = True, passthrough: bool = False
    ) -> str: ...

    # docstr-coverage:excused `overload`
    @overload
    def standardize_uri(
        self, uri: str, *, strict: Literal[False] = False, passthrough: Literal[True] = True
    ) -> str: ...

    # docstr-coverage:excused `overload`
    @overload
    def standardize_uri(
        self, uri: str, *, strict: Literal[False] = False, passthrough: Literal[False] = False
    ) -> Optional[str]: ...

    def standardize_uri(
        self, uri: str, *, strict: bool = False, passthrough: bool = False
    ) -> Optional[str]:
        """Standardize a URI.

        :param uri:
            A string representing a valid uniform resource identifier (URI)
        :param strict: If true and the URI can't be standardized, returns an error. Defaults to false.
        :param passthrough: If true, strict is false, and the URI can't be standardized, return the input.
            Defaults to false.
        :returns:
            A standardized version of the URI in case a URI prefix synonym was used.
            Note that this function is idempotent, i.e., if you give an already
            standard URI, it will just return it as is. If the URI can't be parsed
            with respect to the records in the converter, None is returned.
        :raises URIStandardizationError:
            If strict is true and the URI can't be standardized

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
        >>> converter.standardize_uri("http://example.org/NOPE") is None
        True
        >>> converter.standardize_uri("http://example.org/NOPE", passthrough=True)
        'http://example.org/NOPE'
        """
        prefix, identifier = self.parse_uri(uri)
        if prefix and identifier:
            # prefix is ensured to be in self.prefix_map because of successful parse
            return self.prefix_map[prefix] + identifier
        if strict:
            raise URIStandardizationError(uri)
        if passthrough:
            return uri
        return None

    def pd_compress(
        self,
        df: "pandas.DataFrame",
        column: Union[str, int],
        target_column: Union[None, str, int] = None,
        strict: bool = False,
        passthrough: bool = False,
        ambiguous: bool = False,
    ) -> None:
        """Convert all URIs in the given column to CURIEs.

        :param df: A pandas DataFrame
        :param column: The column in the dataframe containing URIs to convert to CURIEs.
        :param target_column: The column to put the results in. Defaults to input column.
        :param strict: If true and the URI can't be compressed, returns an error. Defaults to false.
        :param passthrough: If true, strict is false, and the URI can't be compressed, return the input.
            Defaults to false.
        :param ambiguous: If true, consider the column as containing either CURIEs or URIs.
        """
        pre_func = self.compress_or_standardize if ambiguous else self.compress
        func = partial(pre_func, strict=strict, passthrough=passthrough)  # type:ignore
        df[column if target_column is None else target_column] = df[column].map(func)

    def pd_expand(
        self,
        df: "pandas.DataFrame",
        column: Union[str, int],
        target_column: Union[None, str, int] = None,
        strict: bool = False,
        passthrough: bool = False,
        ambiguous: bool = False,
    ) -> None:
        """Convert all CURIEs in the given column to URIs.

        :param df: A pandas DataFrame
        :param column: The column in the dataframe containing CURIEs to convert to URIs.
        :param target_column: The column to put the results in. Defaults to input column.
        :param strict: If true and the CURIE can't be expanded, returns an error. Defaults to false.
        :param passthrough: If true, strict is false, and the CURIE can't be expanded, return the input.
            Defaults to false.
        :param ambiguous: If true, consider the column as containing either CURIEs or URIs.
        """
        pre_func = self.expand_or_standardize if ambiguous else self.expand
        func = partial(pre_func, strict=strict, passthrough=passthrough)  # type:ignore
        df[column if target_column is None else target_column] = df[column].map(func)

    def pd_standardize_prefix(
        self,
        df: "pandas.DataFrame",
        *,
        column: Union[str, int],
        target_column: Union[None, str, int] = None,
        strict: bool = False,
        passthrough: bool = False,
    ) -> None:
        """Standardize all prefixes in the given column.

        :param df: A pandas DataFrame
        :param column: The column in the dataframe containing prefixes to standardize.
        :param target_column: The column to put the results in. Defaults to input column.
        :param strict: If true and any prefix can't be standardized, returns an error. Defaults to false.
        :param passthrough: If true, strict is false, and any prefix can't be standardized, return the input.
            Defaults to false.
        """
        func = partial(self.standardize_prefix, strict=strict, passthrough=passthrough)
        df[column if target_column is None else target_column] = df[column].map(func)

    def pd_standardize_curie(
        self,
        df: "pandas.DataFrame",
        *,
        column: Union[str, int],
        target_column: Union[None, str, int] = None,
        strict: bool = False,
        passthrough: bool = False,
    ) -> None:
        r"""Standardize all CURIEs in the given column.

        :param df: A pandas DataFrame
        :param column: The column in the dataframe containing CURIEs to standardize.
        :param target_column: The column to put the results in. Defaults to input column.
        :param strict: If true and any CURIE can't be standardized, returns an error. Defaults to false.
        :param passthrough: If true, strict is false, and any CURIE can't be standardized, return the input.
            Defaults to false.

        The Disease Ontology curates mappings to other semantic spaces and distributes them in the
        tabular SSSOM format. However, they use a wide variety of non-standard prefixes for referring
        to external vocabularies like SNOMED-CT. The Bioregistry contains these synonyms to support
        reconciliation. The following example shows how the SSSOM mappings dataframe can be loaded
        and this function applied to the mapping ``object_id`` column (in place).

        >>> import curies
        >>> import pandas as pd
        >>> commit = "faca4fc335f9a61902b9c47a1facd52a0d3d2f8b"
        >>> url = f"https://raw.githubusercontent.com/mapping-commons/disease-mappings/{commit}/mappings/doid.sssom.tsv"
        >>> df = pd.read_csv(url, sep="\t", comment='#')
        >>> converter = curies.get_bioregistry_converter()
        >>> converter.pd_standardize_curie(df, column="object_id")
        """
        func = partial(self.standardize_curie, strict=strict, passthrough=passthrough)
        df[column if target_column is None else target_column] = df[column].map(func)

    def pd_standardize_uri(
        self,
        df: "pandas.DataFrame",
        *,
        column: Union[str, int],
        target_column: Union[None, str, int] = None,
        strict: bool = False,
        passthrough: bool = False,
    ) -> None:
        """Standardize all URIs in the given column.

        :param df: A pandas DataFrame
        :param column: The column in the dataframe containing URIs to standardize.
        :param target_column: The column to put the results in. Defaults to input column.
        :param strict: If true and any URI can't be standardized, returns an error. Defaults to false.
        :param passthrough: If true, strict is false, and any URI can't be standardized, return the input.
            Defaults to false.
        """
        func = partial(self.standardize_uri, strict=strict, passthrough=passthrough)
        df[column if target_column is None else target_column] = df[column].map(func)

    def file_compress(
        self,
        path: Union[str, Path],
        column: int,
        *,
        sep: Optional[str] = None,
        header: bool = True,
        strict: bool = False,
        passthrough: bool = False,
        ambiguous: bool = False,
    ) -> None:
        """Convert all URIs in the given column of a CSV file to CURIEs.

        :param path: A pandas DataFrame
        :param column: The column in the dataframe containing URIs to convert to CURIEs.
        :param sep: The delimiter of the CSV file, defaults to tab
        :param header: Does the file have a header row?
        :param strict: If true and the URI can't be compressed, returns an error. Defaults to false.
        :param passthrough: If true, strict is false, and the URI can't be compressed, return the input.
            Defaults to false.
        :param ambiguous: If true, consider the column as containing either CURIEs or URIs.
        """
        pre_func = self.compress_or_standardize if ambiguous else self.compress
        func = partial(pre_func, strict=strict, passthrough=passthrough)  # type:ignore
        self._file_helper(func, path=path, column=column, sep=sep, header=header)

    def file_expand(
        self,
        path: Union[str, Path],
        column: int,
        *,
        sep: Optional[str] = None,
        header: bool = True,
        strict: bool = False,
        passthrough: bool = False,
        ambiguous: bool = False,
    ) -> None:
        """Convert all CURIEs in the given column of a CSV file to URIs.

        :param path: A pandas DataFrame
        :param column: The column in the dataframe containing CURIEs to convert to URIs.
        :param sep: The delimiter of the CSV file, defaults to tab
        :param header: Does the file have a header row?
        :param strict: If true and the CURIE can't be expanded, returns an error. Defaults to false.
        :param passthrough: If true, strict is false, and the CURIE can't be expanded, return the input.
            Defaults to false.
        :param ambiguous: If true, consider the column as containing either CURIEs or URIs.
        """
        pre_func = self.expand_or_standardize if ambiguous else self.expand
        func = partial(pre_func, strict=strict, passthrough=passthrough)  # type:ignore
        self._file_helper(func, path=path, column=column, sep=sep, header=header)

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
            if record.prefix == prefix or prefix in record.prefix_synonyms:
                return record
        return None

    def get_subconverter(self, prefixes: Iterable[str]) -> "Converter":
        r"""Get a converter with a subset of prefixes.

        :param prefixes: A list of prefixes to keep from this converter. These can
            correspond either to preferred CURIE prefixes or CURIE prefix synonyms.
        :returns: A new, slimmed down converter

        This functionality is useful for downstream applications like the following:

        1. You load a comprehensive extended prefix map, e.g., from the Bioregistry using
           :func:`curies.get_bioregistry_converter()`.
        2. You load some data that conforms to this prefix map by convention. This
           is often the case for semantic mappings stored in the
           `SSSOM format <https://github.com/mapping-commons/sssom>`_.
        3. You extract the list of prefixes *actually* used within your data
        4. You subset the detailed extended prefix map to only include prefixes
           relevant for your data
        5. You make some kind of output of the subsetted extended prefix map to
           go with your data. Effectively, this is a way of reconciling data. This
           is especially effective when using the Bioregistry or other comprehensive
           extended prefix maps.

        Here's a concrete example of doing this (which also includes a bit of data science)
        to do this on the SSSOM mappings from the `Disease Ontology <https://disease-ontology.org/>`_
        project.

        >>> import curies
        >>> import pandas as pd
        >>> import itertools as itt
        >>> commit = "faca4fc335f9a61902b9c47a1facd52a0d3d2f8b"
        >>> url = f"https://raw.githubusercontent.com/mapping-commons/disease-mappings/{commit}/mappings/doid.sssom.tsv"
        >>> df = pd.read_csv(url, sep="\t", comment='#')
        >>> prefixes = {
        ...     curies.Reference.from_curie(curie).prefix
        ...     for column in ["subject_id", "predicate_id", "object_id"]
        ...     for curie in df[column]
        ... }
        >>> converter = curies.get_bioregistry_converter()
        >>> slim_converter = converter.get_subconverter(prefixes)
        """
        prefixes = set(prefixes)
        records = [
            record
            for record in self.records
            if any(prefix in prefixes for prefix in record._all_prefixes)
        ]
        return Converter(records)


def _eq(a: str, b: str, case_sensitive: bool) -> bool:
    if case_sensitive:
        return a == b
    return a.casefold() == b.casefold()


def _in(a: str, bs: Iterable[str], case_sensitive: bool) -> bool:
    if case_sensitive:
        return a in bs
    nfa = a.casefold()
    return any(nfa == b.casefold() for b in bs)


def chain(converters: Sequence[Converter], *, case_sensitive: bool = True) -> Converter:
    """Chain several converters.

    :param converters: A list or tuple of converters
    :param case_sensitive: If false, will not allow case-sensitive duplicates
    :returns:
        A converter that looks up one at a time in the other converters.
    :raises ValueError:
        If there are no converters

    Chain is the perfect tool if you want to override parts of an existing extended
    prefix map. For example, if you want to use most of the Bioregistry, but you
    would like to specify a custom URI prefix (e.g., using Identifiers.org), you
    can do the following:

    >>> import curies
    >>> bioregistry_converter = curies.get_bioregistry_converter()
    >>> overrides = curies.load_prefix_map({"pubmed": "https://identifiers.org/pubmed:"})
    >>> converter = curies.chain([overrides, bioregistry_converter])
    >>> converter.bimap["pubmed"]
    'https://identifiers.org/pubmed:'

    Similarly, this also works if you want to override a prefix. Keep in mind for this to work
    with a simple prefix map, you need to make sure the URI prefix matches in each converter,
    otherwise you will get duplicates:

    >>> overrides = curies.load_prefix_map({"PMID": "https://www.ncbi.nlm.nih.gov/pubmed/"})
    >>> converter = chain([overrides, bioregistry_converter])
    >>> converter.bimap["PMID"]
    'https://www.ncbi.nlm.nih.gov/pubmed/'

    A safer way is to specify your override using an extended prefix map, which can tie together
    prefix synonyms and URI prefix synonyms:

    >>> import curies
    >>> from curies import Converter, chain, get_bioregistry_converter
    >>> overrides = curies.load_extended_prefix_map([
    ...     {
    ...         "prefix": "PMID",
    ...         "prefix_synonyms": ["pubmed", "PubMed"],
    ...         "uri_prefix": "https://www.ncbi.nlm.nih.gov/pubmed/",
    ...         "uri_prefix_synonyms": [
    ...             "https://identifiers.org/pubmed:",
    ...             "http://bio2rdf.org/pubmed:",
    ...         ],
    ...     },
    ... ])
    >>> converter = curies.chain([overrides, bioregistry_converter])
    >>> converter.bimap["PMID"]
    'https://www.ncbi.nlm.nih.gov/pubmed/'

    Chain prioritizes based on the order given. Therefore, if two prefix maps
    having the same prefix but different URI prefixes are given, the first is retained

    >>> c1 = curies.load_prefix_map({"GO": "http://purl.obolibrary.org/obo/GO_"})
    >>> c2 = curies.load_prefix_map({"GO": "https://identifiers.org/go:"})
    >>> c3 = curies.chain([c1, c2])
    >>> c3.prefix_map["GO"]
    'http://purl.obolibrary.org/obo/GO_'
    """
    if not converters:
        raise ValueError
    rv = Converter([])
    for converter in converters:
        for record in converter.records:
            rv.add_record(record, case_sensitive=case_sensitive, merge=True)
    return rv


def load_prefix_map(prefix_map: LocationOr[Mapping[str, str]], **kwargs: Any) -> Converter:
    """Get a converter from a simple prefix map.

    :param prefix_map:
        One of the following:

        - A mapping whose keys represent CURIE prefixes and values represent URI prefixes
        - A string containing a remote location of a JSON file containg a prefix map
        - A string or :class:`pathlib.Path` object corresponding to a local file path to a JSON file
          containing a prefix map
    :param kwargs: Keyword arguments to pass to :meth:`curies.Converter.__init__`
    :returns:
        A converter

    >>> import curies
    >>> converter = curies.load_prefix_map({
    ...     "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
    ... })
    >>> converter.expand("CHEBI:138488")
    'http://purl.obolibrary.org/obo/CHEBI_138488'
    >>> converter.compress("http://purl.obolibrary.org/obo/CHEBI_138488")
    'CHEBI:138488'
    """
    return Converter.from_prefix_map(prefix_map, **kwargs)


def load_extended_prefix_map(
    records: LocationOr[Iterable[Union[Record, Dict[str, Any]]]], **kwargs: Any
) -> Converter:
    """Get a converter from a list of dictionaries by creating records out of them.

    :param records:
        One of the following:

        - An iterable of :class:`curies.Record` objects or dictionaries that will
          get converted into record objects that together constitute an extended prefix map
        - A string containing a remote location of a JSON file containg an extended prefix map
        - A string or :class:`pathlib.Path` object corresponding to a local file path to a JSON file
          containing an extended prefix map
    :param kwargs: Keyword arguments to pass to :meth:`curies.Converter.__init__`
    :returns: A converter

    An extended prefix map is a list of dictionaries containing four keys:

    1. A ``prefix`` string
    2. A ``uri_prefix`` string
    3. An optional list of strings ``prefix_synonyms``
    4. An optional list of strings ``uri_prefix_synonyms``

    Across the whole list of dictionaries, there should be uniqueness within
    the union of all ``prefix`` and ``prefix_synonyms`` as well as uniqueness
    within the union of all ``uri_prefix`` and ``uri_prefix_synonyms``.

    >>> import curies
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
    >>> converter = curies.load_extended_prefix_map(epm)

    Expand using the preferred/canonical prefix:

    >>> converter.expand("CHEBI:138488")
    'http://purl.obolibrary.org/obo/CHEBI_138488'

    Expand using a prefix synonym:

    >>> converter.expand("chebi:138488")
    'http://purl.obolibrary.org/obo/CHEBI_138488'

    Compress using the preferred/canonical URI prefix:

    >>> converter.compress("http://purl.obolibrary.org/obo/CHEBI_138488")
    'CHEBI:138488'

    Compressing using a URI prefix synonym:

    >>> converter.compress("https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:138488")
    'CHEBI:138488'

    Example from a remote source:

    >>> url = "https://github.com/biopragmatics/bioregistry/raw/main/exports/contexts/bioregistry.epm.json"
    >>> converter = curies.load_extended_prefix_map(url)
    """
    return Converter.from_extended_prefix_map(records, **kwargs)


def load_jsonld_context(data: LocationOr[Dict[str, Any]], **kwargs: Any) -> Converter:
    """Get a converter from a JSON-LD object, which contains a prefix map in its ``@context`` key.

    :param data:
        A JSON-LD object
    :param kwargs: Keyword arguments to pass to :meth:`curies.Converter.__init__`
    :return:
        A converter

    Example from a remote context file:

    >>> base = "https://raw.githubusercontent.com"
    >>> url = f"{base}/biopragmatics/bioregistry/main/exports/contexts/semweb.context.jsonld"
    >>> converter = Converter.from_jsonld(url)
    >>> "rdf" in converter.prefix_map
    """
    return Converter.from_jsonld(data, **kwargs)


def load_shacl(data: LocationOr["rdflib.Graph"], **kwargs: Any) -> Converter:
    """Get a converter from a JSON-LD object, which contains a prefix map in its ``@context`` key.

    :param data:
        A path to an RDF file or a RDFlib graph
    :param kwargs: Keyword arguments to pass to :meth:`curies.Converter.__init__`
    :return:
        A converter
    """
    return Converter.from_shacl(data, **kwargs)


def write_extended_prefix_map(converter: Converter, path: Union[str, Path]) -> None:
    """Write an extended prefix map as JSON to a file."""
    path = _ensure_path(path)
    path.write_text(
        json.dumps(
            [_record_to_dict(record) for record in converter.records],
            indent=4,
            sort_keys=True,
            ensure_ascii=False,
        )
    )


def _record_to_dict(record: Record) -> Mapping[str, Union[str, List[str]]]:
    """Convert a record to a dict."""
    rv: Dict[str, Union[str, List[str]]] = {
        "prefix": record.prefix,
        "uri_prefix": record.uri_prefix,
    }
    if record.prefix_synonyms:
        rv["prefix_synonyms"] = sorted(record.prefix_synonyms)
    if record.uri_prefix_synonyms:
        rv["uri_prefix_synonyms"] = sorted(record.uri_prefix_synonyms)
    if record.pattern:
        rv["pattern"] = record.pattern
    return rv


def _ensure_path(path: Union[str, Path]) -> Path:
    if isinstance(path, str):
        path = Path(path).resolve()
    return path


def _get_jsonld_context(
    converter: Converter, *, expand: bool = False, include_synonyms: bool = False
) -> Dict[str, Any]:
    """Get a JSON-LD context based on the converter."""
    context = {}
    for record in converter.records:
        term = _get_expanded_term(record, expand=expand)
        context[record.prefix] = term
        if include_synonyms:
            for prefix_synonym in record.prefix_synonyms:
                context[prefix_synonym] = term
    return {"@context": context}


def write_jsonld_context(
    converter: Converter,
    path: Union[str, Path],
    *,
    include_synonyms: bool = False,
    expand: bool = False,
) -> None:
    """Write the converter's bijective map as a JSON-LD context to a file.

    :param converter: The converter to export
    :param path: The path to a file to write to
    :param include_synonyms: If true, includes CURIE prefix synonyms.
        URI prefix synonyms are not output.
    :param expand: If False, output a dictionary-like ``@context`` element.
        If True, use ``@prefix`` and ``@id`` as keys for the CURIE prefix
        and URI prefix, respectively, to maximize compatibility.

    The following example shows writing a JSON-LD context:

    .. code-block:: python

        import curies
        converter = curies.load_prefix_map({
            "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        })
        curies.write_jsonld_context(converter, "example_context.json")

    .. code-block:: json

        {
          "@context": {
            "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_"
          }
        }

    Because some implementations of JSON-LD do not like URI prefixes that end
    with an underscore ``_``, we can use the ``expand`` keyword to turn on more
    verbose JSON-LD context output that contains explicit ``@prefix`` and
    ``@id`` annotations

    .. code-block:: python

        import curies
        converter = curies.load_prefix_map({
            "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        })
        curies.write_jsonld_context(converter, "example_context.json", expand=True)

    .. code-block:: json

        {
          "@context": {
            "CHEBI": {
              "@id": "http://purl.obolibrary.org/obo/CHEBI_",
              "@prefix": true
            }
          }
        }
    """
    path = _ensure_path(path)
    obj = _get_jsonld_context(converter, include_synonyms=include_synonyms, expand=expand)
    with path.open("w") as file:
        json.dump(obj, file, indent=4, sort_keys=True)


def _get_expanded_term(record: Record, *, expand: bool) -> Union[str, Dict[str, Any]]:
    if not expand:
        return record.uri_prefix

    # Use expanded term definition described in https://www.w3.org/TR/json-ld11/#expanded-term-definition
    rv = {"@prefix": True, "@id": record.uri_prefix}
    # TODO add an @context inside here to somehow capture the pattern, if available
    # if record.pattern:
    #     rv["@context"] = {
    #         "sh": "http://www.w3.org/ns/shacl#",
    #         "sh:pattern": record.pattern,
    #     }
    return rv


def write_shacl(
    converter: Converter,
    path: Union[str, Path],
    *,
    include_synonyms: bool = False,
) -> None:
    """Write the converter's bijective map as SHACL in turtle RDF to a file.

    :param converter: The converter to export
    :param path: The path to a file to write to
    :param include_synonyms: If true, includes CURIE prefix synonyms.
        URI prefix synonyms are not output.

    .. seealso:: https://www.w3.org/TR/shacl/#sparql-prefixes

    .. code-block:: python

        import curies
        converter = curies.load_prefix_map({
            "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        })
        curies.write_shacl(converter, "example_shacl.ttl")

    .. code-block::

        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        [
          sh:declare
            [ sh:prefix "CHEBI" ; sh:namespace "http://purl.obolibrary.org/obo/CHEBI_"^^xsd:anyURI  ]
        ] .
    """
    text = dedent(
        """\
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        [
          sh:declare
        {entries}
        ] .
        """
    )
    path = _ensure_path(path)
    lines = []
    for record in converter.records:
        lines.append(_get_shacl_line(record.prefix, record.uri_prefix, pattern=record.pattern))
        if include_synonyms:
            for prefix_synonym in record.prefix_synonyms:
                lines.append(
                    _get_shacl_line(prefix_synonym, record.uri_prefix, pattern=record.pattern)
                )
    path.write_text(text.format(entries=",\n".join(lines)))


def write_tsv(
    converter: Converter, path: Union[str, Path], *, header: Tuple[str, str] = ("prefix", "base")
) -> None:
    """Write a simple prefix map CSV file.

    :param converter: The converter to export
    :param path: The path to a file to write to
    :param header: A 2-tuple of strings representing the header used in the file,
        where the first element is the label for CURIE prefixes and the second
        element is the label for URI prefixes

    .. code-block:: python

        import curies
        converter = curies.load_prefix_map({
            "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        })
        curies.write_tsv(converter, "example_context.tsv")

    .. code-block::

        prefix  base
        CHEBI   http://purl.obolibrary.org/obo/CHEBI_
    """
    import csv

    path = _ensure_path(path)

    with path.open("w") as csvfile:
        writer = csv.writer(csvfile, delimiter="\t")
        writer.writerow(header)
        for record in converter.records:
            writer.writerow((record.prefix, record.uri_prefix))


def _get_shacl_line(prefix: str, uri_prefix: str, pattern: Optional[str] = None) -> str:
    line = f'    [ sh:prefix "{prefix}" ; sh:namespace "{uri_prefix}"^^xsd:anyURI '
    if pattern:
        pattern = pattern.replace("\\", "\\\\")
        line += f'; sh:pattern "{pattern}"'
    return line + " ]"


def upgrade_prefix_map(prefix_map: Mapping[str, str]) -> List[Record]:
    """Convert a (potentially problematic) prefix map (i.e., not bijective) into a list of records.

    A prefix map is bijective if it has no duplicate CURIE prefixes (i.e., keys in a dictionary) and
    no duplicate URI prefixes (i.e., values in a dictionary). Because of the way that dictionaries work in Python,
    we are always guaranteed that there are no duplicate keys.

    However, it is both possible and frequent to have duplicate values. This happens because many semantic spaces
    have multiple synonymous CURIE prefixes. For example, the `OBO in OWL <https://bioregistry.io/oboinowl>`_
    vocabulary has two common, interchangable prefixes: ``oio`` and ``oboInOwl`` (and the case variant ``oboinowl``).
    Therefore, a prefix map might contain the following parts that make it non-bijective:

    .. code-block:: json

        {
          "oio": "http://www.geneontology.org/formats/oboInOwl#",
          "oboInOwl": "http://www.geneontology.org/formats/oboInOwl#"
        }

    This is bad because this prefix map can't be used to determinstically compress a URI. For example, should
    ``http://www.geneontology.org/formats/oboInOwl#hasDbXref`` be compressed to ``oio:hasDbXref`` or
    ``oboInOwl:hasDbXref``? Neither is necessarily incorrect, but the issue here is that there is not an explicit
    choice by the data modeler, meaning that data compressed into CURIEs with this non-bijective map might not be
    readily integrable with other datasets.

    The best solution to this situation is not more code, but rather for the data modeler to address the issue
    upstream in the following steps:

    1. Choose the which of prefix synonyms is going to be the primary prefix. If you're not sure, the
       `Bioregistry <https://bioregistry.io/>`_ is a comprehensive registry of prefixes and their syonyms
       applicable in the semantic web and the natural sciences. It gives a good suggestion of what the best
       prefix is. In the OBO in OWL case, it suggests ``oboInOwl``.
    2. Update all related data artifacts to only use that preferred prefix
    3. Either 1) remove the other synonyms (in this example, ``oio``) from the prefix map *or* 2) transition to
       using :ref:`epms`, a more modern data structure for supporting URI and CURIE interconversion.

    The first part of step 3 in this solution highlights one of the key shortcomings of prefix maps themselves -
    they can't keep track of synonyms, which are often useful in data integration, especially when a single
    prefix map is defined on the level of a project or community. The extended prefix map is a simple data structure
    proposed to address this.

    * * *

    This function is for people who are not in the position to make the sustainable fix, and want to automate
    the assignment of which is the preferred prefix. It uses a deterministic algorithm to choose from two or more
    CURIE prefixes that have the same URI prefix and generate an extended prefix map in which they have bene collapsed
    into a single record. More specitically, the algorithm is based on a case-sensitive lexical sort of the prefixes.
    The first in the sort order becomes the primary prefix and the others become synonyms in the resulting record.

    :param prefix_map: A mapping whose keys represent CURIE prefixes and values represent URI prefixes
    :return: A list of :class:`curies.Record` objects that together constitute an extended prefix map

    >>> from curies import Converter, upgrade_prefix_map
    >>> pm = {"a": "https://example.com/a/", "b": "https://example.com/a/"}
    >>> records = upgrade_prefix_map(pm)
    >>> converter = Converter(records)
    >>> converter.expand("a:1")
    'https://example.com/a/1'
    >>> converter.expand("b:1")
    'https://example.com/a/1'
    >>> converter.compress("https://example.com/a/1")
    'a:1'

    .. note::

        Thanks to `Joe Flack <https://github.com/joeflack4>`_ for proposing this algorithm
        `in this discussion <https://github.com/mapping-commons/sssom-py/pull/485#discussion_r1451812733>`_.

    """
    uri_prefix_to_curie_synonyms = defaultdict(list)
    for curie_prefix, uri_prefix in prefix_map.items():
        uri_prefix_to_curie_synonyms[uri_prefix].append(curie_prefix)
    priority_prefix_map = {
        uri_prefix: sorted(curie_prefixes)
        for uri_prefix, curie_prefixes in uri_prefix_to_curie_synonyms.items()
    }
    return [
        Record(prefix=prefix, prefix_synonyms=prefix_synonyms, uri_prefix=uri_prefix)
        for uri_prefix, (prefix, *prefix_synonyms) in sorted(priority_prefix_map.items())
    ]
