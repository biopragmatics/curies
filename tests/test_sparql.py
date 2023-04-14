"""Tests federated SPARQL queries between the curies mapping service and popular triplestores."""

import itertools as itt
import unittest
from textwrap import dedent
from typing import Collection, NamedTuple, Set, Tuple

from curies.mapping_service.utils import (
    get_sparql_record_so_tuples,
    get_sparql_records,
    sparql_service_available,
)

# NOTE: federated queries need to use docker internal URL
LOCAL_MAPPING_SERVICE = "http://localhost:8888/sparql"
LOCAL_BLAZEGRAPH = "http://localhost:8889/blazegraph/namespace/kb/sparql"
LOCAL_VIRTUOSO = "http://localhost:8890/sparql"
LOCAL_FUSEKI = "http://localhost:8891/mapping"

DOCKER_MAPPING_SERVICE = "http://mapping-service:8888/sparql"
DOCKER_BLAZEGRAPH = "http://blazegraph:8080/blazegraph/namespace/kb/sparql"
DOCKER_VIRTUOSO = "http://virtuoso:8890/sparql"
DOCKER_FUSEKI = "http://fuseki:3030/mapping"

#: Some triplestores are a bit picky on the mime types to use, e.g. blazegraph
#: SELECT query fails when asking for application/xml, so we need to use a subset
#: of content types for the federated tests
TEST_CONTENT_TYPES = {
    "application/json",
    "application/sparql-results+xml",
    "text/csv",
}


class TripleStoreConfiguation(NamedTuple):
    """A tuple with information for each triplestore."""

    local_endpoint: str
    docker_endpoint: str
    mimetypes: Collection[str]
    direct_queries: Collection[str]
    service_query_fmts: Collection[str]


def get_pairs(endpoint: str, sparql: str, accept: str) -> Set[Tuple[str, str]]:
    """Get a response from a given SPARQL query."""
    records = get_sparql_records(endpoint=endpoint, sparql=sparql, accept=accept)
    return get_sparql_record_so_tuples(records)


SPARQL_TO_MAPPING_SERVICE_VALUES = f"""\
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?s ?o WHERE {{
    SERVICE <{DOCKER_MAPPING_SERVICE}> {{
        VALUES ?s {{ <http://purl.obolibrary.org/obo/CHEBI_24867> <http://purl.obolibrary.org/obo/CHEBI_24868> }} .
        ?s owl:sameAs ?o .
    }}
}}
""".rstrip()

SPARQL_TO_MAPPING_SERVICE_SIMPLE = f"""\
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?s ?o WHERE {{
    SERVICE <{DOCKER_MAPPING_SERVICE}> {{
        <http://purl.obolibrary.org/obo/CHEBI_24867> owl:sameAs ?o .
        ?s owl:sameAs ?o .
    }}
}}
""".rstrip()

SPARQL_FROM_MAPPING_SERVICE_SIMPLE = """\
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT ?s ?o WHERE {{
    <http://purl.obolibrary.org/obo/CHEBI_24867> owl:sameAs ?s .
    SERVICE <{0}> {{
        ?s a ?o .
    }}
}}
""".rstrip()

configurations = {
    "blazegraph": TripleStoreConfiguation(
        local_endpoint=LOCAL_BLAZEGRAPH,
        docker_endpoint=DOCKER_BLAZEGRAPH,
        mimetypes=TEST_CONTENT_TYPES,
        direct_queries=[SPARQL_TO_MAPPING_SERVICE_SIMPLE, SPARQL_TO_MAPPING_SERVICE_VALUES],
        service_query_fmts=[SPARQL_FROM_MAPPING_SERVICE_SIMPLE],
    ),
    "virtuoso": TripleStoreConfiguation(
        local_endpoint=LOCAL_VIRTUOSO,
        docker_endpoint=DOCKER_VIRTUOSO,
        mimetypes=TEST_CONTENT_TYPES,  # todo generalize?
        # TODO: Virtuoso fails to resolves VALUES in federated query
        direct_queries=[SPARQL_TO_MAPPING_SERVICE_SIMPLE],
        service_query_fmts=[SPARQL_FROM_MAPPING_SERVICE_SIMPLE],
    ),
}


# @require_service(LOCAL_MAPPING_SERVICE, "Mapping")
class TestSPARQL(unittest.TestCase):
    """Tests federated SPARQL queries between the curies mapping service and blazegraph/virtuoso triplestores.

    Run and init the required triplestores locally:
    1. docker compose up
    2. ./tests/resources/init_triplestores.sh
    """

    def assert_endpoint(self, endpoint: str, query: str, *, accept: str):
        """Assert the endpoint returns favorable results."""
        records = get_pairs(endpoint, query, accept=accept)
        self.assertIn(
            ("http://purl.obolibrary.org/obo/CHEBI_24867", "https://bioregistry.io/chebi:24867"),
            records,
        )

    # @require_service(LOCAL_VIRTUOSO, "Virtuoso")
    def test_from_virtuoso_to_mapping_service(self):
        """Test a federated query from a OpenLink Virtuoso triplestore to the curies service."""
        self.assertTrue(sparql_service_available(LOCAL_VIRTUOSO))
        for mimetype in TEST_CONTENT_TYPES:
            with self.subTest(mimetype=mimetype):
                self.assert_endpoint(
                    LOCAL_VIRTUOSO, SPARQL_TO_MAPPING_SERVICE_SIMPLE, accept=mimetype
                )
                # TODO: Virtuoso fails to resolves VALUES in federated query
                # self.assert_endpoint(LOCAL_VIRTUOSO, SPARQL_TO_MAPPING_SERVICE_VALUES, accept=mimetype)

    def test_from_triplestore(self):
        """Test federated queries from various triples stores to the CURIEs service."""
        for name, config in configurations.items():
            self.assertTrue(sparql_service_available(config.local_endpoint))
            for mimetype, sparql in itt.product(config.mimetypes, config.direct_queries):
                with self.subTest(name=name, mimetype=mimetype, sparql=sparql):
                    self.assert_endpoint(config.local_endpoint, sparql, accept=mimetype)

    def test_to_triplestore(self):
        """Test a federated query from the CURIEs service to various triple stores."""
        for name, config in configurations.items():
            # TODO mismatch between local/docker?
            self.assertTrue(sparql_service_available(config.local_endpoint))
            for mimetype, query_fmt in itt.product(config.mimetypes, config.service_query_fmts):
                sparql = dedent(query_fmt.format(config.docker_endpoint).rstrip())
                with self.subTest(name=name, mimetype=mimetype, sparql=sparql):
                    records = get_pairs(LOCAL_MAPPING_SERVICE, sparql, accept=mimetype)
                    self.assertGreater(len(records), 0)

    # @require_service(LOCAL_VIRTUOSO, "Virtuoso")
    def test_from_mapping_service_to_virtuoso(self):
        """Test a federated query from the curies service to a OpenLink Virtuoso triplestore."""
        self.assertTrue(sparql_service_available(LOCAL_VIRTUOSO))
        query = dedent(SPARQL_FROM_MAPPING_SERVICE_SIMPLE.format(DOCKER_VIRTUOSO).rstrip())
        for mimetype in TEST_CONTENT_TYPES:
            with self.subTest(mimetype=mimetype):
                records = get_pairs(LOCAL_MAPPING_SERVICE, query, accept=mimetype)
                self.assertGreater(len(records), 0)

    # @require_service(LOCAL_BLAZEGRAPH, "Blazegraph")
    def test_from_blazegraph_to_mapping_service(self):
        """Test a federated query from a Blazegraph triplestore to the curies service."""
        self.assertTrue(sparql_service_available(LOCAL_BLAZEGRAPH))
        for mimetype in TEST_CONTENT_TYPES:
            with self.subTest(mimetype=mimetype):
                self.assert_endpoint(
                    LOCAL_BLAZEGRAPH, SPARQL_TO_MAPPING_SERVICE_SIMPLE, accept=mimetype
                )
                self.assert_endpoint(
                    LOCAL_BLAZEGRAPH, SPARQL_TO_MAPPING_SERVICE_VALUES, accept=mimetype
                )

    # @require_service(LOCAL_BLAZEGRAPH, "Blazegraph")
    def test_from_mapping_service_to_blazegraph(self):
        """Test a federated query from the curies service to a OpenLink Virtuoso triplestore."""
        self.assertTrue(sparql_service_available(LOCAL_BLAZEGRAPH))
        query = dedent(SPARQL_FROM_MAPPING_SERVICE_SIMPLE.format(DOCKER_BLAZEGRAPH).rstrip())
        for mimetype in TEST_CONTENT_TYPES:
            with self.subTest(mimetype=mimetype):
                records = get_pairs(LOCAL_MAPPING_SERVICE, query, accept=mimetype)
                self.assertGreater(len(records), 0)

    def test_from_fuseki_to_mapping_service(self):
        """Test a federated query from a OpenLink Virtuoso triplestore to the curies service."""
        self.assertTrue(sparql_service_available(LOCAL_FUSEKI))
        for mimetype in TEST_CONTENT_TYPES:
            with self.subTest(mimetype=mimetype):
                self.assert_endpoint(LOCAL_FUSEKI, SPARQL_TO_MAPPING_SERVICE_SIMPLE, accept=mimetype)
                self.assert_endpoint(LOCAL_FUSEKI, SPARQL_TO_MAPPING_SERVICE_VALUES, accept=mimetype)

    def test_from_mapping_service_to_fuseki(self):
        """Test a federated query from the curies service to a OpenLink Virtuoso triplestore."""
        self.assertTrue(sparql_service_available(LOCAL_FUSEKI))
        query = dedent(SPARQL_FROM_MAPPING_SERVICE_SIMPLE.format(DOCKER_FUSEKI).rstrip())
        for mimetype in TEST_CONTENT_TYPES:
            with self.subTest(mimetype=mimetype):
                records = get_pairs(LOCAL_MAPPING_SERVICE, query, accept=mimetype)
                self.assertGreater(len(records), 0)