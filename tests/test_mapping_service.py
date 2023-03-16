# -*- coding: utf-8 -*-

"""Tests for the identifier mapping service."""

import json
import unittest
from typing import Iterable, Set, Tuple
from urllib.parse import quote

from fastapi.testclient import TestClient
from rdflib import OWL, SKOS
from rdflib.query import ResultRow

from curies import Converter
from curies.mapping_service import (
    MappingServiceGraph,
    MappingServiceSPARQLProcessor,
    _prepare_predicates,
    get_fastapi_mapping_app,
    get_flask_mapping_app,
)

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
        self.graph = MappingServiceGraph(converter=self.converter)
        self.processor = MappingServiceSPARQLProcessor(self.graph)

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

    def test_safe_expand(self):
        """Test that expansion to invalid prefixes doesn't happen."""
        ppm = {
            "CHEBI": [
                "http://purl.obolibrary.org/obo/CHEBI_",
                "http://identifiers.org/chebi/",
                "http://identifiers.org/chebi/nope nope:",
            ],
        }
        converter = Converter.from_priority_prefix_map(ppm)
        graph = MappingServiceGraph(converter=converter)
        self.assertEqual(
            {"http://purl.obolibrary.org/obo/CHEBI_1", "http://identifiers.org/chebi/1"},
            set(map(str, graph._expand_pair_all("http://purl.obolibrary.org/obo/CHEBI_1"))),
        )


class ConverterMixin(unittest.TestCase):
    """A mixin that has a converter."""

    def setUp(self) -> None:
        """Set up the test case with a converter."""
        super().setUp()
        self.converter = Converter.from_priority_prefix_map(PREFIX_MAP)

    def assert_get_sparql_results(self, client, sparql):
        """Test a sparql query returns expected values."""
        res = client.get(f"/sparql?query={quote(sparql)}")
        self.assertEqual(200, res.status_code, msg=f"Response: {res}\n\n{res.text}")
        records = {
            (record["s"]["value"], record["o"]["value"])
            for record in json.loads(res.text)["results"]["bindings"]
        }
        self.assertEqual(EXPECTED, records)


class TestFlaskMappingWeb(ConverterMixin):
    """Test the Flask-based mapping service."""

    def setUp(self) -> None:
        """Set up the test case with a converter and app."""
        super().setUp()
        self.app = get_flask_mapping_app(self.converter)

    def assert_post_sparql_results(self, client, sparql):
        """Test a sparql query returns expected values."""
        res = client.post("/sparql", json={"query": sparql})
        self.assertEqual(
            200, res.status_code, msg=f"\nRequest: {res.request}\nResponse: {res}\n\n{res.json}"
        )
        records = {
            (record["s"]["value"], record["o"]["value"])
            for record in json.loads(res.text)["results"]["bindings"]
        }
        self.assertEqual(EXPECTED, records)

    def test_get_missing_query(self):
        """Test error on missing query parameter."""
        with self.app.test_client() as client:
            res = client.get("/sparql")
            self.assertEqual(400, res.status_code, msg=f"Response: {res}")

    def test_post_missing_query(self):
        """Test error on missing query parameter."""
        with self.app.test_client() as client:
            res = client.post("/sparql")
            self.assertEqual(400, res.status_code, msg=f"Response: {res}")

    def test_get_query(self):
        """Test querying the app with GET."""
        with self.app.test_client() as client:
            self.assert_get_sparql_results(client, SPARQL_SIMPLE)

    def test_post_query(self):
        """Test querying the app with POST."""
        with self.app.test_client() as client:
            self.assert_post_sparql_results(client, SPARQL_SIMPLE)

    def test_get_service_query(self):
        """Test sparql generated by a service (that has values outside of where clause) with GET."""
        with self.app.test_client() as client:
            self.assert_get_sparql_results(client, SPARQL_FROM_SERVICE)

    def test_post_service_query(self):
        """Test sparql generated by a service (that has values outside of where clause) with POST."""
        with self.app.test_client() as client:
            self.assert_post_sparql_results(client, SPARQL_FROM_SERVICE)


class TestFastAPIMappingApp(ConverterMixin):
    """Test the FastAPI-based mapping service."""

    def setUp(self) -> None:
        """Set up the test case with a converter, blueprint, and app."""
        super().setUp()
        self.app = get_fastapi_mapping_app(self.converter)
        self.client = TestClient(self.app)

    def assert_post_sparql_results(self, client, sparql):
        """Test a sparql query returns expected values."""
        res = client.post("/sparql", json={"query": sparql})
        self.assertEqual(
            200,
            res.status_code,
            msg=f"Response: {res}",
        )
        records = {
            (record["s"]["value"], record["o"]["value"])
            for record in res.json()["results"]["bindings"]
        }
        self.assertEqual(EXPECTED, records)

    def test_get_missing_query(self):
        """Test error on missing query parameter."""
        res = self.client.get("/sparql")
        self.assertEqual(422, res.status_code, msg=f"Response: {res}")

    def test_post_missing_query(self):
        """Test error on missing query parameter."""
        res = self.client.post("/sparql")
        self.assertEqual(422, res.status_code, msg=f"Response: {res}")

    def test_get_query(self):
        """Test querying the app with GET."""
        self.assert_get_sparql_results(self.client, SPARQL_SIMPLE)

    def test_post_query(self):
        """Test querying the app with POST."""
        self.assert_post_sparql_results(self.client, SPARQL_SIMPLE)

    def test_get_service_query(self):
        """Test sparql generated by a service (that has values outside of where clause) with GET."""
        self.assert_get_sparql_results(self.client, SPARQL_FROM_SERVICE)

    def test_post_service_query(self):
        """Test sparql generated by a service (that has values outside of where clause) with POST."""
        self.assert_post_sparql_results(self.client, SPARQL_FROM_SERVICE)
