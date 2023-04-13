# -*- coding: utf-8 -*-

"""Utilities for the mapping service."""

import json
import json.decoder
import unittest
from typing import Callable, List, Mapping, Optional, Set, Tuple

import requests
from defusedxml import ElementTree

__all__ = [
    "handle_csv",
    "handle_json",
    "handle_xml",
    "CONTENT_TYPE_TO_HANDLER",
    "get_sparql_records",
    "sparql_service_available",
    "handle_header",
]

Record = Mapping[str, str]
Records = List[Record]

#: A SPARQL query used to ping a SPARQL endpoint
PING_SPARQL = 'SELECT ?s ?o WHERE { BIND("hello" as ?s) . BIND("there" as ?o) . }'

#: This is default for federated queries
DEFAULT_CONTENT_TYPE = "application/sparql-results+xml"

#: A mapping from content types to the keys used for serializing
#: in :meth:`rdflib.Graph.serialize` and other serialization functions
CONTENT_TYPE_TO_RDFLIB_FORMAT = {
    # https://www.w3.org/TR/sparql11-results-json/
    "application/sparql-results+json": "json",
    # https://www.w3.org/TR/rdf-sparql-XMLres/
    "application/sparql-results+xml": "xml",
    # https://www.w3.org/TR/sparql11-results-csv-tsv/
    "application/sparql-results+csv": "csv",
}

#: A dictionary that maps synonym content types to the canonical ones
CONTENT_TYPE_SYNONYMS = {
    "application/json": "application/sparql-results+json",
    "text/json": "application/sparql-results+json",
    "application/xml": "application/sparql-results+xml",
    "text/xml": "application/sparql-results+xml",
    "text/csv": "application/sparql-results+csv",
}


def handle_json(text: str) -> Records:
    """Parse bindings encoded in a JSON string."""
    data = json.loads(text)
    return [
        {key: value["value"] for key, value in record.items()}
        for record in data["results"]["bindings"]
    ]


def handle_xml(text: str) -> Records:
    """Parse bindings encoded in an XML string."""
    root = ElementTree.fromstring(text)
    results = root.find("{http://www.w3.org/2005/sparql-results#}results")
    return [
        {
            binding.attrib["name"]: binding.find("{http://www.w3.org/2005/sparql-results#}uri").text
            for binding in result
        }
        for result in results
    ]


def handle_csv(text: str) -> Records:
    """Parse bindings encoded in a CSV string."""
    header, *lines = (line.strip().split(",") for line in text.splitlines())
    return [dict(zip(header, line)) for line in lines]


#: A mapping from canonical content types to functions for parsing them
CONTENT_TYPE_TO_HANDLER: Mapping[str, Callable[[str], Records]] = {
    "application/sparql-results+json": handle_json,
    "application/sparql-results+xml": handle_xml,
    "application/sparql-results+csv": handle_csv,
}


def get_sparql_records(endpoint: str, sparql: str, accept: str) -> Records:
    """Get a response from a given SPARQL query."""
    res = requests.get(
        endpoint,
        params={"query": sparql},
        headers={"accept": accept},
    )
    res.raise_for_status()
    func = CONTENT_TYPE_TO_HANDLER[handle_header(accept)]
    return func(res.text)


def get_sparql_record_so_tuples(records: Records) -> Set[Tuple[str, str]]:
    """Get subject/object pairs from records."""
    return {(record["s"], record["o"]) for record in records}


def sparql_service_available(endpoint: str) -> bool:
    """Test if a SPARQL service is running."""
    try:
        records = get_sparql_records(endpoint, PING_SPARQL, "application/json")
    except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError):
        return False
    return {("hello", "there")} == get_sparql_record_so_tuples(records)


def _handle_part(part: str) -> Tuple[str, float]:
    if ";q=" not in part:
        return part, 1.0
    key, q = part.split(";q=", 1)
    return key, float(q)


def handle_header(header: Optional[str]) -> str:
    """Canonicalize the a header."""
    if not header:
        return DEFAULT_CONTENT_TYPE

    parts = dict(_handle_part(part) for part in header.split(","))

    # Sort in descending order of q value
    for header in sorted(parts, key=parts.__getitem__, reverse=True):
        header = CONTENT_TYPE_SYNONYMS.get(header, header)
        if header in CONTENT_TYPE_TO_RDFLIB_FORMAT:
            return header
        # What happens if encountering "*/*" that has a higher q than something else?
        # Is that even possible/coherent?

    return DEFAULT_CONTENT_TYPE


def require_service(url: str, name: str):  # type:ignore
    """Skip a test unless the service is available."""
    return unittest.skipUnless(
        sparql_service_available(url), reason=f"No {name} service is running on {url}"
    )
