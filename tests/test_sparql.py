"""Tests federated SPARQL queries between the curies mapping service and popular triplestores."""

import unittest
from typing import Set, Tuple

from tests.test_federated_sparql import _get_so
from tests.test_federated_sparql import get as fget
from tests.test_federated_sparql import sparql_service_available
from tests.test_mapping_service import VALID_CONTENT_TYPES

PING_SPARQL = 'SELECT ?s ?o WHERE { BIND("hello" as ?s) . BIND("there" as ?o) . }'
# NOTE: federated queries need to use docker internal URL
DOCKER_BIOREGISTRY = "http://mapping-service:8888/sparql"
LOCAL_BIOREGISTRY = "http://localhost:8888/sparql"
LOCAL_BLAZEGRAPH = "http://localhost:8889/blazegraph/namespace/kb/sparql"
DOCKER_BLAZEGRAPH = "http://blazegraph:8080/blazegraph/namespace/kb/sparql"
LOCAL_VIRTUOSO = "http://localhost:8890/sparql"
DOCKER_VIRTUOSO = "http://virtuoso:8890/sparql"


def get(endpoint: str, sparql: str, accept: str) -> Set[Tuple[str, str]]:
    """Get a response from a given SPARQL query."""
    return _get_so(fget(endpoint=endpoint, sparql=sparql, accept=accept))


SPARQL_VALUES = f"""\
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?s ?o WHERE {{
    SERVICE <{DOCKER_BIOREGISTRY}> {{
        VALUES ?s {{ <http://purl.obolibrary.org/obo/CHEBI_24867> <http://purl.obolibrary.org/obo/CHEBI_24868> }} .
        ?s owl:sameAs ?o .
    }}
}}
""".rstrip()

SPARQL_SIMPLE = f"""\
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?s ?o WHERE {{
    SERVICE <{DOCKER_BIOREGISTRY}> {{
        <http://purl.obolibrary.org/obo/CHEBI_24867> owl:sameAs ?o .
        ?s owl:sameAs ?o .
    }}
}}
""".rstrip()


@unittest.skipUnless(
    sparql_service_available(LOCAL_BIOREGISTRY), reason="No local Bioregistry is running"
)
class TestSPARQL(unittest.TestCase):
    """Tests federated SPARQL queries between the curies mapping service and blazegraph/virtuoso triplestores.

    Run and init the required triplestores locally:
    1. docker compose up
    2. ./tests/resources/init_triplestores.sh
    """

    def assert_endpoint(self, endpoint: str, query: str, *, accept: str):
        """Assert the endpoint returns favorable results."""
        records = get(endpoint, query, accept=accept)
        self.assertIn(
            ("http://purl.obolibrary.org/obo/CHEBI_24867", "https://bioregistry.io/chebi:24867"),
            records,
        )

    @unittest.skipUnless(
        sparql_service_available(LOCAL_BLAZEGRAPH), reason="No local BlazeGraph is running"
    )
    def test_from_blazegraph_to_bioregistry(self):
        """Test a federated query from a Blazegraph triplestore to the curies service."""
        for mimetype in VALID_CONTENT_TYPES:
            with self.subTest(mimetype=mimetype):
                self.assert_endpoint(LOCAL_BLAZEGRAPH, SPARQL_SIMPLE, accept=mimetype)
                self.assert_endpoint(LOCAL_BLAZEGRAPH, SPARQL_VALUES, accept=mimetype)

    @unittest.skipUnless(
        sparql_service_available(LOCAL_VIRTUOSO), reason="No local Virtuoso is running"
    )
    def test_from_virtuoso_to_bioregistry(self):
        """Test a federated query from a OpenLink Virtuoso triplestore to the curies service."""
        for mimetype in VALID_CONTENT_TYPES:
            with self.subTest(mimetype=mimetype):
                self.assert_endpoint(LOCAL_VIRTUOSO, SPARQL_SIMPLE, accept=mimetype)
                # TODO: Virtuoso fails to resolves VALUES in federated query
                # self.assert_endpoint(LOCAL_VIRTUOSO, SPARQL_VALUES, accept=mimetype)

    @unittest.skipUnless(
        sparql_service_available(LOCAL_BIOREGISTRY), reason="No local Bioregistry is running"
    )
    def test_from_bioregistry_to_virtuoso(self):
        """Test a federated query from the curies service to a OpenLink Virtuoso triplestore."""
        query = f"""\
SELECT ?s ?o WHERE {{
    <https://identifiers.org/uniprot/P07862> <http://www.w3.org/2002/07/owl#sameAs> ?s .
    SERVICE <{DOCKER_VIRTUOSO}> {{
        ?s ?p ?o .
    }}
}}
""".rstrip()
        for mimetype in VALID_CONTENT_TYPES:
            with self.subTest(mimetype=mimetype):
                records = get(LOCAL_BIOREGISTRY, query, accept=mimetype)
                self.assertGreater(len(records), 0)

    @unittest.skipUnless(
        sparql_service_available(LOCAL_BIOREGISTRY), reason="No local Bioregistry is running"
    )
    def test_from_bioregistry_to_blazegraph(self):
        """Test a federated query from the curies service to a OpenLink Virtuoso triplestore."""
        query = f"""\
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX bl: <https://w3id.org/biolink/vocab/>
SELECT ?s ?o WHERE {{
  <https://www.ensembl.org/id/ENSG00000006453> owl:sameAs ?s .

  SERVICE <{DOCKER_BLAZEGRAPH}> {{
      ?s bl:category ?o .
  }}
}}
""".rstrip()
        for mimetype in VALID_CONTENT_TYPES:
            with self.subTest(mimetype=mimetype):
                records = get(LOCAL_BIOREGISTRY, query, accept=mimetype)
                self.assertGreater(len(records), 0)
