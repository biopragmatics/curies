# -*- coding: utf-8 -*-

"""Tests for the identifier mapping service."""

import json
import unittest
from typing import Iterable, Set, Tuple
from urllib.parse import quote

from rdflib import OWL, SKOS
from rdflib.query import ResultRow

from curies import Converter
from curies.mapping_service import CURIEServiceGraph, _prepare_predicates, get_flask_mapping_app
from curies.mapping_service.rdflib_custom import JervenSPARQLProcessor

PREFIX_MAP = {
    "CHEBI": [
        "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=",
        "http://identifiers.org/chebi/",
        "http://purl.obolibrary.org/obo/CHEBI_",
    ],
    "GO": ["http://purl.obolibrary.org/obo/GO_"],
    "OBO": ["http://purl.obolibrary.org/obo/"],
}

SPARQL_SIMPLE = """\
SELECT DISTINCT ?s ?o WHERE {
    VALUES ?s {
        <http://purl.obolibrary.org/obo/CHEBI_1>
        <http://purl.obolibrary.org/obo/CHEBI_2>
    }
    ?s owl:sameAs ?o
}
""".rstrip()

SPARQL_SIMPLE_BACKWARDS = """\
SELECT DISTINCT ?s ?o WHERE {
    VALUES ?o {
        <http://purl.obolibrary.org/obo/CHEBI_1>
        <http://purl.obolibrary.org/obo/CHEBI_2>
    }
    ?s owl:sameAs ?o
}
""".rstrip()

#: This represents a SPARQL query that happens when a service generates it
SPARQL_FROM_SERVICE = """\
SELECT REDUCED * WHERE {
    ?s owl:sameAs ?o .
}
VALUES (?s) {
    (<http://purl.obolibrary.org/obo/CHEBI_1>)
    (<http://purl.obolibrary.org/obo/CHEBI_2>)
}
"""

EXPECTED = {
    (
        "http://purl.obolibrary.org/obo/CHEBI_1",
        "http://purl.obolibrary.org/obo/CHEBI_1",
    ),
    ("http://purl.obolibrary.org/obo/CHEBI_1", "http://identifiers.org/chebi/1"),
    (
        "http://purl.obolibrary.org/obo/CHEBI_1",
        "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=1",
    ),
    (
        "http://purl.obolibrary.org/obo/CHEBI_2",
        "http://purl.obolibrary.org/obo/CHEBI_2",
    ),
    ("http://purl.obolibrary.org/obo/CHEBI_2", "http://identifiers.org/chebi/2"),
    (
        "http://purl.obolibrary.org/obo/CHEBI_2",
        "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=2",
    ),
}


def _stm(rows: Iterable[ResultRow]) -> Set[Tuple[str, str]]:
    return {(str(row.s), str(row.o)) for row in rows}


class TestMappingService(unittest.TestCase):
    """Test the identifier mapping service."""

    def setUp(self) -> None:
        """Set up the converter."""
        self.converter = Converter.from_priority_prefix_map(PREFIX_MAP)
        self.graph = CURIEServiceGraph(converter=self.converter)
        self.processor = JervenSPARQLProcessor(self.graph)

    def test_prepare_predicates(self):
        """Test preparation of predicates."""
        self.assertEqual({OWL.sameAs}, _prepare_predicates())
        self.assertEqual({OWL.sameAs}, _prepare_predicates(OWL.sameAs))
        self.assertEqual(
            {OWL.sameAs, SKOS.exactMatch}, _prepare_predicates({OWL.sameAs, SKOS.exactMatch})
        )

    def test_errors(self):
        """Test errors."""
        for sparql in [
            # errors because of unbound subject
            "SELECT ?s ?o WHERE { ?s owl:sameAs ?o }",
            # errors because of bad predicate
            "SELECT ?o WHERE { <http://purl.obolibrary.org/obo/CHEBI_1> rdfs:seeAlso ?o }",
            "SELECT ?s WHERE { ?s rdfs:seeAlso <http://purl.obolibrary.org/obo/CHEBI_1> }",
            # errors because of unknown URI
            "SELECT ?o WHERE { <http://example.com/1> owl:sameAs ?o }",
            "SELECT ?s WHERE { ?s owl:sameAs <http://example.com/1> }",
            # errors because predicate is given
            "SELECT * WHERE { <http://purl.obolibrary.org/obo/CHEBI_1> "
            "owl:sameAs <http://purl.obolibrary.org/obo/CHEBI_1> }",
        ]:
            with self.subTest(sparql=sparql):
                self.assertEqual([], list(self.graph.query(sparql, processor=self.processor)))

    def test_sparql(self):
        """Test a sparql query on the graph."""
        rows = _stm(self.graph.query(SPARQL_SIMPLE, processor=self.processor))
        self.assertNotEqual(0, len(rows), msg="No results were returned")
        self.assertEqual(EXPECTED, rows)

    def test_sparql_backwards(self):
        """Test a sparql query on the graph."""
        rows = _stm(self.graph.query(SPARQL_SIMPLE_BACKWARDS, processor=self.processor))
        self.assertNotEqual(0, len(rows), msg="No results were returned")
        expected = {(o, s) for s, o in EXPECTED}
        self.assertEqual(expected, rows)

    def test_service_sparql(self):
        """Test the SPARQL that gets sent when using this as a service."""
        rows = _stm(self.graph.query(SPARQL_FROM_SERVICE, processor=self.processor))
        self.assertNotEqual(0, len(rows), msg="No results were returned")
        self.assertEqual(EXPECTED, rows)

    def test_missing(self):
        """Test a sparql query on the graph where the URIs can't be parsed."""
        sparql = """\
            SELECT ?s ?o WHERE {
                VALUES ?s { <http://example.org/1> <http://example.org/1> }
                ?s owl:sameAs ?o
            }
        """
        self.assertEqual([], list(self.graph.query(sparql, processor=self.processor)))


class TestMappingWeb(unittest.TestCase):
    """Test the web component of the mapping service."""

    def setUp(self) -> None:
        """Set up the test case with a converter and app."""
        self.converter = Converter.from_priority_prefix_map(PREFIX_MAP)
        self.app = get_flask_mapping_app(self.converter)

    def test_query(self):
        """Test querying the app."""
        with self.app.test_client() as client:
            self.assert_sparql_results(client, SPARQL_SIMPLE)

    def test_service_query(self):
        """Test sparql generated by a service (that has values outside of where clause)."""
        with self.app.test_client() as client:
            self.assert_sparql_results(client, SPARQL_FROM_SERVICE)

    def test_missing_query(self):
        """Test error on missing query parameter."""
        with self.app.test_client() as client:
            res = client.get("/sparql")
            self.assertEqual(400, res.status_code, msg=f"Response: {res}")

    def assert_sparql_results(self, client, sparql):
        """Test a sparql query returns expected values."""
        res = client.get(f"/sparql?query={quote(sparql)}")
        self.assertEqual(200, res.status_code, msg=f"Response: {res}")
        records = {
            (record["s"]["value"], record["o"]["value"])
            for record in json.loads(res.text)["results"]["bindings"]
        }
        self.assertEqual(EXPECTED, records)
