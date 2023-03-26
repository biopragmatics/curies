# -*- coding: utf-8 -*-

"""Utilities for the mapping service."""

import json
from typing import Callable, List, Mapping

from defusedxml.etree import ElementTree

__all__ = [
    "handle_csv",
    "handle_json",
    "handle_xml",
    "HANDLE",
]

Record = Mapping[str, str]
Records = List[Record]


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
HANDLE: Mapping[str, Callable[[str], Records]] = {
    "application/sparql-results+json": handle_json,
    "application/sparql-results+xml": handle_xml,
    "application/sparql-results+csv": handle_csv,
}
