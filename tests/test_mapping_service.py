# -*- coding: utf-8 -*-

"""Tests for the identifier mapping service."""

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
    get_fastapi_mapping_app,
    get_flask_mapping_app,
)
from curies.mapping_service.api import _prepare_predicates
from curies.mapping_service.utils import (
    CONTENT_TYPE_SYNONYMS,
    CONTENT_TYPE_TO_HANDLER,
    handle_header,
    sparql_service_available,
)

VALID_CONTENT_TYPES = {
    *CONTENT_TYPE_TO_HANDLER,
    "",
    "*/*",
    *CONTENT_TYPE_SYNONYMS,
}

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

    def test_parse_header(self):
        """Test parsing a rather complex header."""
        example_header = (
            "application/sparql-results+xml;q=0.8,"
            "application/xml;q=0.8,"
            "application/x-binary-rdf-results-table,"
            "application/sparql-results+json;q=0.8,"
            "application/json;q=0.8,"
            "text/csv;q=0.8,"
            "text/tab-separated-values;q=0.8"
        )
        content_type = handle_header(example_header)
        self.assertEqual("application/sparql-results+xml", content_type)

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

    def assert_mimetype(self, res, content_type):
        """Assert the correct MIMETYPE."""
        content_type = handle_header(content_type)
        mimetype = getattr(res, "mimetype", None)
        if hasattr(res, "mimetype"):  # this is from Flask
            self.assertEqual(content_type, mimetype)
        else:  # this is from FastAPI
            actual_content_type = res.headers.get("content-type")
            self.assertIsNotNone(actual_content_type)
            self.assertEqual(content_type, actual_content_type.split(";")[0].strip())

    def assert_parsed(self, res, content_type: str):
        """Test the result has the expected output."""
        content_type = handle_header(content_type)
        parse_func = CONTENT_TYPE_TO_HANDLER[content_type]
        records = parse_func(res.text)
        pairs = {(record["s"], record["o"]) for record in records}
        self.assertEqual(EXPECTED, pairs)

    def assert_get_sparql_results(self, client, sparql):
        """Test a sparql query returns expected values."""
        for content_type in sorted(VALID_CONTENT_TYPES):
            with self.subTest(content_type=content_type):
                res = client.get(f"/sparql?query={quote(sparql)}", headers={"accept": content_type})
                self.assertEqual(200, res.status_code, msg=f"Response: {res}\n\n{res.text}")
                self.assert_mimetype(res, content_type)
                self.assert_parsed(res, content_type)

    def assert_post_sparql_results(self, client, sparql):
        """Test a sparql query returns expected values."""
        for content_type in sorted(VALID_CONTENT_TYPES):
            with self.subTest(content_type=content_type):
                res = client.post(
                    # note that we're using "data" and not JSON since this service
                    # is posting "form data" and not a JSON payload
                    "/sparql",
                    data={"query": sparql},
                    headers={"accept": content_type},
                )
                self.assertEqual(
                    200,
                    res.status_code,
                    msg=f"Response: {res}",
                )
                self.assert_mimetype(res, content_type)
                self.assert_parsed(res, content_type)


class TestFlaskMappingWeb(ConverterMixin):
    """Test the Flask-based mapping service."""

    def setUp(self) -> None:
        """Set up the test case with a converter and app."""
        super().setUp()
        self.app = get_flask_mapping_app(self.converter)

    def test_get_missing_query(self):
        """Test error on missing query parameter."""
        with self.app.test_client() as client:
            for content_type in sorted(VALID_CONTENT_TYPES):
                with self.subTest(content_type=content_type):
                    res = client.get("/sparql", headers={"accept": content_type})
                    self.assertEqual(400, res.status_code, msg=f"Response: {res}")

    def test_post_missing_query(self):
        """Test error on missing query parameter."""
        with self.app.test_client() as client:
            for content_type in sorted(VALID_CONTENT_TYPES):
                with self.subTest(content_type=content_type):
                    res = client.post("/sparql", headers={"accept": content_type})
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

    def test_get_missing_query(self):
        """Test error on missing query parameter."""
        for content_type in sorted(VALID_CONTENT_TYPES):
            with self.subTest(content_type=content_type):
                res = self.client.get("/sparql", headers={"accept": content_type})
                self.assertEqual(422, res.status_code, msg=f"Response: {res}")

    def test_post_missing_query(self):
        """Test error on missing query parameter."""
        for content_type in sorted(VALID_CONTENT_TYPES):
            with self.subTest(content_type=content_type):
                res = self.client.post("/sparql", headers={"accept": content_type})
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


class TestUtils(unittest.TestCase):
    """Test utilities."""

    def test_availability(self):
        """Test sparql service availability check."""
        self.assertTrue(
            sparql_service_available("https://query.wikidata.org/bigdata/namespace/wdq/sparql")
        )
        self.assertFalse(sparql_service_available("https://example.org"))
