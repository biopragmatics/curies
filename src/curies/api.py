# -*- coding: utf-8 -*-

"""Data structures and algorithms for :mod:`curies`."""

import csv
import itertools as itt
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, List, Mapping, Optional, Sequence, Set, Tuple, Union

import requests
from pytrie import StringTrie

if TYPE_CHECKING:  # pragma: no cover
    import pandas

__all__ = [
    "Converter",
    "DuplicateURIPrefixes",
    "chain",
]


@dataclass
class Record:
    """A record of some prefixes and their associated URI prefixes."""

    #: The canonical prefix, used in the reverse prefix map
    prefix: str
    #: The canonical URI prefix, used in the forward prefix map
    uri_prefix: str
    prefix_synonyms: List[str] = field(default_factory=list)
    uri_prefix_synonyms: List[str] = field(default_factory=list)

    @property
    def _all_prefixes(self):
        return [self.prefix, *self.prefix_synonyms]

    @property
    def _all_uri_prefixes(self):
        return [self.uri_prefix, *self.uri_prefix_synonyms]


class DuplicateURIPrefixes(ValueError):
    """An error raised with constructing a converter with data containing duplicate URI prefixes."""

    def __init__(self, duplicates: List[Tuple[str, str, str]]):
        """Initialize the error."""
        self.duplicates = duplicates

    def __str__(self) -> str:  # noqa:D105
        text = "\n".join("\t".join(duplicate) for duplicate in self.duplicates)
        return f"Duplicate URIs:\n{text}"


def _get_duplicate_uri_prefixes(records: List[Record]) -> List[Tuple[Record, Record, str]]:
    rv = [
        (record_1, record_2, uri_prefix)
        for record_1, record_2 in itt.combinations(records, 2)
        for uri_prefix, up2 in itt.product(record_1._all_uri_prefixes, record_2._all_uri_prefixes)
        if uri_prefix == up2
    ]


def _get_duplicate_prefixes(records: List[Record]) -> List[Tuple[Record, Record, str]]:
    rv = [
        (record_1, record_2, prefix)
        for record_1, record_2 in itt.combinations(records, 2)
        for prefix, p2 in itt.product(record_1._all_prefixes, record_2._all_prefixes)
        if prefix == p2
    ]


def _get_prefix_map(records: List[Record]) -> Mapping[str, str]:
    rv = {}
    for record in records:
        rv[record.prefix] = record.uri_prefix
        for prefix_synonym in record.prefix_synonyms:
            rc[prefix_synonym] = record.uri_prefix
    return rv


def _get_reverse_prefix_map(records: List[Record]) -> Mapping[str, str]:
    rv = {}
    for record in records:
        rv[record.uri_prefix] = record.prefix
        for uri_prefix_synonym in record.uri_prefix_synonyms:
            rv[uri_prefix_synonym] = record.prefix
    return rv


class Converter:
    """A cached prefix map data structure.

    .. code-block::

        Construct a prefix map:
        >>> converter = Converter.from_prefix_map({
        ...    "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        ...    "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
        ...    "GO": "http://purl.obolibrary.org/obo/GO_",
        ...    "OBO": "http://purl.obolibrary.org/obo/",
        ... })

        Compression and Expansion:
        >>> converter.compress("http://purl.obolibrary.org/obo/CHEBI_1")
        'CHEBI:1'
        >>> converter.expand("CHEBI:1")
        'http://purl.obolibrary.org/obo/CHEBI_1'

        Example with unparsable URI:
        >>> converter.compress("http://example.com/missing:0000000")

        Example with missing prefix:
        >>> converter.expand("missing:0000000")
    """

    #: The expansion dictionary with prefixes as keys and priority URI prefixes as values
    prefix_map: Mapping[str, str]
    #: The mapping from URI prefixes to prefixes
    reverse_prefix_map: Mapping[str, str]
    #: A prefix trie for efficient parsing of URIs
    trie: StringTrie

    def __init__(self, records: List[Record], *, delimiter: str = ":", strict: bool = True):
        """Instantiate a converter.

        :param records:
            A prefix map where the keys are prefixes (e.g., `chebi`)
            and the values are lists of URI prefixes (e.g., `http://purl.obolibrary.org/obo/CHEBI_`)
            with the first element of the list being the priority URI prefix for expansions.
        :param strict:
            If true, raises issues on duplicate URI prefixes
        :param delimiter:
            The delimiter used for CURIEs. Defaults to a colon.
        :raises DuplicateURIPrefixes: if any prefixes share any URI prefixes
        """
        if strict:
            duplicate_uri_prefixes = _get_duplicate_uri_prefixes(records)
            if duplicate_uri_prefixes:
                raise DuplicateURIPrefixes(duplicate_uri_prefixes)
            duplicate_prefixes = _get_duplicate_prefixes(records)
            if duplicate_prefixes:
                raise DuplicateURIPrefixes(duplicate_prefixes)

        self.delimiter = delimiter
        self.records = records
        self.prefix_map = _get_prefix_map(records)
        self.reverse_prefix_map = _get_reverse_prefix_map(records)
        self.trie = StringTrie(self.reverse_prefix_map)

    @classmethod
    def from_priority_prefix_map(cls, data: Mapping[str, List[str]], **kwargs) -> "Converter":
        return cls(
            [
                Record(
                    prefix=prefix, uri_prefix=uri_prefixes[0], uri_prefix_synonyms=uri_prefixes[1:]
                )
                for prefix, uri_prefixes in data.items()
            ],
            **kwargs,
        )

    @classmethod
    def from_prefix_map(cls, prefix_map: Mapping[str, str]) -> "Converter":
        """Get a converter from a simple prefix map.

        :param prefix_map:
            A mapping whose keys are prefixes and whose values are the corresponding *URI prefixes*).

            .. note::

                It's possible that some *URI prefixes* (values in this mapping)
                partially overlap (e.g.,``http://purl.obolibrary.org/obo/GO_`` for the prefix ``GO`` and
                ``http://purl.obolibrary.org/obo/`` for the prefix ``OBO``). The longest URI prefix will always
                be matched. For example, parsing ``http://purl.obolibrary.org/obo/GO_0032571``
                will return ``GO:0032571`` instead of ``OBO:GO_0032571``.
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
                for prefix, uri_prefix in prefix_map.items()
            ]
        )

    @classmethod
    def from_reverse_prefix_map(cls, reverse_prefix_map: Mapping[str, str]) -> "Converter":
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
        """
        dd = defaultdict(list)
        for uri_prefix, prefix in reverse_prefix_map.items():
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
    def from_reverse_prefix_map_url(cls, url: str) -> "Converter":
        """Get a remote reverse prefix map JSON file then parse with :meth:`Converter.from_reverse_prefix_map`.

        :param url:
            A URL to a reverse prefix map JSON file
        :return:
            A converter
        """
        res = requests.get(url)
        res.raise_for_status()
        return cls.from_reverse_prefix_map(res.json())

    @classmethod
    def from_jsonld(cls, data) -> "Converter":
        """Get a converter from a JSON-LD object, which contains a prefix map in its ``@context`` key.

        :param data:
            A JSON-LD object
        :return:
            A converter
        """
        return cls.from_prefix_map(data["@context"])

    @classmethod
    def from_jsonld_url(cls, url: str) -> "Converter":
        """Get a remote JSON-LD file then parse with :meth:`Converter.from_jsonld`.

        :param url:
            A URL to a JSON-LD file
        :return:
            A converter

        >>> base = "https://raw.githubusercontent.com"
        >>> url = f"{base}/biopragmatics/bioregistry/main/exports/contexts/semweb.context.jsonld"
        >>> converter = Converter.from_jsonld_url(url)
        >>> "rdf" in converter.prefix_map
        True
        """
        res = requests.get(url)
        res.raise_for_status()
        return cls.from_jsonld(res.json())

    @classmethod
    def from_jsonld_github(cls, owner: str, repo: str, *path: str, branch: str = "main"):
        """Construct a remote JSON-LD URL on GitHub then parse with :meth:`Converter.from_jsonld_url`.

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
        ...     "biopragmatics", "bioregistry", "exports", "contexts", "semweb.context.jsonld"
        ... )
        >>> "rdf" in converter.prefix_map
        True
        """
        if not path or not path[-1].endswith(".jsonld"):
            raise ValueError("final path argument should end with .jsonld")
        rest = "/".join(path)
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{rest}"
        return cls.from_jsonld_url(url)

    def get_prefixes(self) -> Set[str]:
        """Get the set of prefixes covered by this converter."""
        return set(self.prefix_map)

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
        if prefix is not None and identifier is not None:
            return f"{prefix}{self.delimiter}{identifier}"
        return None

    def parse_uri(self, uri: str) -> Union[Tuple[str, str], Tuple[None, None]]:
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
            return prefix, uri[len(value) :]

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
        prefix, identifier = curie.split(self.delimiter, 1)
        return self.expand_pair(prefix, identifier)

    def expand_pair(self, prefix: str, identifier: str) -> Optional[str]:
        """Expand a CURIE pair to a URI.

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

    def file_compress(
        self, path: Union[str, Path], column: int, sep: Optional[str] = None, header: bool = True
    ):
        """Convert all URIs in the given column of a CSV file to CURIEs.

        :param path: A pandas DataFrame
        :param column: The column in the dataframe containing URIs to convert to CURIEs.
        :param sep: The delimiter of the CSV file, defaults to tab
        :param header: Does the file have a header row?
        """
        self._file_helper(self.compress, path=path, column=column, sep=sep, header=header)

    def file_expand(
        self, path: Union[str, Path], column: int, sep: Optional[str] = None, header: bool = True
    ):
        """Convert all CURIEs in the given column of a CSV file to URIs.

        :param path: A pandas DataFrame
        :param column: The column in the dataframe containing CURIEs to convert to URIs.
        :param sep: The delimiter of the CSV file, defaults to tab
        :param header: Does the file have a header row?
        """
        self._file_helper(self.expand, path=path, column=column, sep=sep, header=header)

    @staticmethod
    def _file_helper(
        func, path: Union[str, Path], column: int, sep: Optional[str] = None, header: bool = True
    ):
        path = Path(path).expanduser().resolve()
        rows = []
        delimiter = sep or "\t"
        with path.open() as file_in:
            reader = csv.reader(file_in, delimiter=delimiter)
            _header = next(reader) if header else None
            for row in reader:
                row[column] = func(row[column])
                rows.append(row)
        with path.open("w") as file_out:
            writer = csv.writer(file_out, delimiter=delimiter)
            if _header:
                writer.writerow(_header)
            writer.writerows(rows)


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

    key_to_canonical = {}
    #: A mapping from the canonical key to the primary URI expansion
    head = {}
    #: A mapping from the canonical key to the secondary URI expansions
    tails = defaultdict(set)
    for converter in converters:
        for prefix, uri_prefixes in converter.data.items():
            key = prefix if case_sensitive else prefix.casefold()
            canonical = key_to_canonical.get(key)
            if canonical is None:
                canonical = key_to_canonical[key] = prefix
                head[canonical] = uri_prefixes[0]
                tails[canonical].update(uri_prefixes[1:])
            else:
                tails[canonical].update(uri_prefixes)

    # Make sure none of the tails have the head in them
    for key, uri_prefixes in tails.items():
        uri_prefixes.remove(head[key])

    data = {prefix: [uri_prefix, *sorted(tails[prefix])] for prefix, uri_prefix in head.items()}
    return Converter(data)


def _norm(s: str) -> str:
    return s.lower().replace("-", "").replace(".", "").replace("_", "").replace(" ", "")
