# -*- coding: utf-8 -*-

"""Data structures and algorithms for :mod:`curies`."""

from typing import Mapping, Optional, Tuple, Union

import requests
from pytrie import StringTrie

__all__ = [
    "Converter",
]


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
        >>> converter.expand("CHEBI", "1")
        'http://purl.obolibrary.org/obo/CHEBI_1'

        Example with unparsable URI:
        >>> converter.compress("http://example.com/nope")

        Example with missing prefix:
        >>> converter.expand("xxx", "1")
    """

    def __init__(self, *, prefix_map: Mapping[str, str], delimiter: str = ":"):
        """Instantiate a converter.

        :param prefix_map:
            A prefix map where the keys are prefixes (e.g., `chebi`)
            and the values are URI prefixes (e.g., `http://purl.obolibrary.org/obo/CHEBI_`).
        :param delimiter:
            The delimiter used for CURIEs. Defaults to a colon.

        .. warning::

            The ``Converter.__init__`` is subject to change to accommodate more complex
            prefix map formulations, so it's best to use class methods like :meth:`from_prefix_map`
            to instantiate Converter objects.
        """
        self.delimiter = delimiter
        self.data = dict(prefix_map)
        self.trie = StringTrie(**{uri_prefix: prefix for prefix, uri_prefix in self.data.items()})

    @classmethod
    def from_prefix_map(cls, prefix_map: Mapping[str, str]) -> "Converter":
        """Get a converter from a simple prefix map.

        :param prefix_map:
            A mapping whose keys are prefixes and whose values are the corresponding URI prefixes
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
        return cls(prefix_map=prefix_map)

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
        >>> "rdf" in converter.data
        True
        """
        res = requests.get(url)
        res.raise_for_status()
        return cls.from_jsonld(res.json())

    @classmethod
    def from_jsonld_github(cls, owner: str, repo: str, *path: str):
        """Construct a remote JSON-LD URL on GitHub then parse with :meth:`Converter.from_jsonld_url`.

        :param owner: A github repository owner or organization (e.g., ``biopragmatics``)
        :param repo: The name of the repository (e.g., ``bioregistry``)
        :param path: The file path in the GitHub repository to a JSON-LD context file.
        :return:
            A converter
        :raises ValueError:
            If the given path doesn't end in a .jsonld file name

        >>> converter = Converter.from_jsonld_github(
        ...     "biopragmatics", "bioregistry", "exports", "contexts", "semweb.context.jsonld"
        ... )
        >>> "rdf" in converter.data
        True
        """
        if not path[-1].endswith(".jsonld"):
            raise ValueError("final path argument should end with .jsonld")
        rest = "/".join(path)
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{rest}"
        return cls.from_jsonld_url(url)

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
        >>> converter.compress("http://purl.obolibrary.org/obo/CHEBI_138488")
        ('CHEBI', '138488')
        >>> converter.compress("http://example.org/missing:0000000")
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
        uri_prefix = self.data.get(prefix)
        if uri_prefix is None:
            return None
        return uri_prefix + identifier
