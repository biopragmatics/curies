"""Utilities for the mapping service."""

from __future__ import annotations

import json
import json.decoder
import unittest
from collections.abc import Mapping
from typing import Callable

from defusedxml import ElementTree

__all__ = [
    "CONTENT_TYPE_TO_HANDLER",
    "get_sparql_records",
    "handle_csv",
    "handle_header",
    "handle_json",
    "handle_xml",
    "parse_header",
    "sparql_service_available",
]

Record = Mapping[str, str]
Records = list[Record]

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
    import requests

    res = requests.get(
        endpoint,
        timeout=60,
        params={"query": sparql},
        headers={"accept": accept},
    )
    res.raise_for_status()
    func = CONTENT_TYPE_TO_HANDLER[handle_header(accept)]
    return func(res.text)


def get_sparql_record_so_tuples(records: Records) -> set[tuple[str, str]]:
    """Get subject/object pairs from records."""
    return {(record["s"], record["o"]) for record in records}


def sparql_service_available(endpoint: str) -> bool:
    """Test if a SPARQL service is running."""
    try:
        records = get_sparql_records(endpoint, PING_SPARQL, "application/json")
    except (OSError, json.decoder.JSONDecodeError):
        return False
    return {("hello", "there")} == get_sparql_record_so_tuples(records)


def _handle_part(part: str) -> tuple[str, float]:
    if ";q=" not in part:
        return part, 1.0
    key, q = part.split(";q=", 1)
    return key, float(q)


def parse_header(header: str) -> list[str]:
    """Parse the header and sort in descending order of q value."""
    parts = dict(_handle_part(part) for part in header.split(","))
    return sorted(parts, key=parts.__getitem__, reverse=True)


def handle_header(header: str | None, default: str = DEFAULT_CONTENT_TYPE) -> str:
    """Canonicalize a header."""
    if not header:
        return default

    for header_part in parse_header(header):
        header_part = CONTENT_TYPE_SYNONYMS.get(header_part, header_part)
        if header_part in CONTENT_TYPE_TO_RDFLIB_FORMAT:
            return header_part
        # What happens if encountering "*/*" that has a higher q than something else?
        # Is that even possible/coherent?

    return default


def require_service(url: str, name: str):  # type:ignore
    """Skip a test unless the service is available."""
    return unittest.skipUnless(
        sparql_service_available(url), reason=f"No {name} service is running on {url}"
    )
