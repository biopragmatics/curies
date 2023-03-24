# -*- coding: utf-8 -*-

"""Tests federated SPARQL queries to an identifier mapping service deployed publicly.

TODO: we might want to add checks if the endpoints are up, and skip the test if not up
"""

import subprocess
import time
import unittest
from multiprocessing import Process
from textwrap import dedent

import pystow
import requests
import uvicorn

from curies import Converter
from curies.mapping_service import get_fastapi_mapping_app
from tests.test_mapping_service import PREFIX_MAP

BIOREGISTRY_SPARQL_ENDPOINT = "http://bioregistry.io/sparql"
TEST_QUERY = 'SELECT ?test WHERE { BIND("hello" as ?test) }'


class FederationMixin(unittest.TestCase):
    """A shared mixin for testing."""

    def get(
        self, endpoint: str, sparql: str, *, accept: str = "application/json"
    ) -> requests.Response:
        """Get a response from a given SPARQL query."""
        response = requests.get(
            endpoint,
            params={"query": sparql},
            headers={"accept": accept},
        )
        return response

    def assert_service_works(self, endpoint: str):
        """Assert that a service is able to accept a simple SPARQL query."""
        res = self.get(endpoint, TEST_QUERY, accept="application/json")
        res_json = res.json()
        self.assertIn("results", res_json)
        self.assertIn("bindings", res_json["results"])
        self.assertEqual(1, len(res_json["results"]["bindings"]))
        self.assertIn("test", res_json["results"]["bindings"][0])
        self.assertIn("value", res_json["results"]["bindings"][0]["test"])
        self.assertEqual("hello", res_json["results"]["bindings"][0]["test"]["value"])


class TestPublicFederatedSPARQL(FederationMixin):
    """Test the identifier mapping service."""

    def setUp(self) -> None:
        """Set up the public federated SPARQL test case."""
        self.sparql = dedent(
            f"""\
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT DISTINCT ?o WHERE {{
            SERVICE <{BIOREGISTRY_SPARQL_ENDPOINT}> {{
                <http://purl.obolibrary.org/obo/CHEBI_24867> owl:sameAs ?o
            }}
        }}
        """.rstrip()
        )

    def query_endpoint(self, endpoint: str):
        """Query an endpoint."""
        self.assert_service_works(endpoint)

        accept = "application/sparql-results+json"
        resp = self.get(endpoint, self.sparql, accept=accept)
        self.assertEqual(
            200,
            resp.status_code,
            msg=f"SPARQL query failed at {endpoint}:\n\n{self.sparql}\n\nResponse:\n{resp.text}",
        )
        response_content_type = resp.headers["content-type"].split(";")[0]
        self.assertEqual(accept, response_content_type, msg="Server sent incorrect content type")

        try:
            res = resp.json()
        except Exception:
            self.fail(msg=f"\n\nError running the federated query to {endpoint}:\n{resp.text}")
        self.assertGreater(
            len(res["results"]["bindings"]),
            0,
            msg=f"Federated query to {endpoint} gives no results",
        )
        self.assertIn(
            "https://bioregistry.io/chebi:24867",
            {binding["o"]["value"] for binding in res["results"]["bindings"]},
        )

    def test_public_federated_virtuoso(self):
        """Test sending a federated query to a public mapping service from Virtuoso."""
        self.query_endpoint("https://bio2rdf.org/sparql")

    def test_public_federated_blazegraph(self):
        """Test sending a federated query to a public mapping service from Blazegraph."""
        self.query_endpoint("http://kg-hub-rdf.berkeleybop.io/blazegraph/sparql")

    def test_public_federated_graphdb(self):
        """Test sending a federated query to a public mapping service from GraphDB."""
        self.query_endpoint("https://graphdb.dumontierlab.com/repositories/test")


def _get_app():
    converter = Converter.from_priority_prefix_map(PREFIX_MAP)
    app = get_fastapi_mapping_app(converter)
    return app


class TestFederatedSparql(FederationMixin):
    """Test the identifier mapping service."""

    proc: Process
    proc_blazegraph: Process

    def assert_blazegraph_running(self):
        """Check that blazegraph is running properly."""
        self.assert_service_works(self.blazegraph_endpoint)

    def setUp(self):
        """Set up the test case."""
        self.blazegraph_jar_path = pystow.ensure(
            "blazegraph",
            url="https://github.com/blazegraph/database/releases/download/BLAZEGRAPH_2_1_6_RC/blazegraph.jar",
        )
        self.blazegraph_port = 9999
        self.blazegraph_endpoint = (
            f"http://localhost:{self.blazegraph_port}/blazegraph/namespace/kb/sparql"
        )

        try:
            self.get(self.blazegraph_endpoint, TEST_QUERY)
        except requests.exceptions.ConnectionError:
            pass
        else:
            self.fail(msg="Expected a connection error. This means blazegraph is already running")

        # Start Blazegraph SPARQL endpoint
        self.proc_blazegraph = Process(
            target=subprocess.run,
            args=([f"java -jar {self.blazegraph_jar_path.as_posix()}"]),
            kwargs={
                "shell": True,
            },
            daemon=True,
        )
        self.proc_blazegraph.start()
        time.sleep(1)
        self.assert_blazegraph_running()

        # NOTE: Try using rdflib-endpoint instead of the curies mapping service
        # import rdflib
        # from rdflib_endpoint import SparqlEndpoint
        # g = rdflib.Graph()
        # g.add((rdflib.URIRef("http://s"), rdflib.URIRef("http://p"), rdflib.URIRef("http://o")))
        # app = SparqlEndpoint(graph=g)

        # Start the curies mapping service SPARQL endpoint
        self.proc = Process(
            target=uvicorn.run,
            # uvicorn.run accepts a zero-argument callable that returns an app
            args=(_get_app,),
            # kwargs={"host": "localhost", "port": 8000, "log_level": "info"},
            daemon=True,
        )
        self.proc.start()

        self.mapping_service = "http://localhost:8000/sparql"  # TODO get from app/configure app
        self.sparql = f"""\
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT DISTINCT ?o WHERE {{
            SERVICE <{self.mapping_service}> {{
                ?s ?p ?o
            }}
        }}
        """.rstrip()

    def tearDown(self):
        """Tear down the testing case."""
        # TODO: blazegraph not actually killed, it will continue to run afterward
        # Not sure how to make sure a java subprocess running as daemon is killed
        # self.proc_blazegraph.kill()
        self.proc.kill()

        # manual instructions for cancelling process:
        # 1. shell: ps aux | grep blaze
        # 2. find the number of the process
        # 3. shell: kill #

    def test_federated_local_blazegraph(self):
        """Test sending a federated query to a local mapping service from a local Blazegraph."""
        resp = self.get(self.blazegraph_endpoint, self.sparql)
        try:
            res = resp.json()
            self.assertGreater(
                len(res["results"]["bindings"]),
                0,
                msg=f"Federated query to {self.blazegraph_endpoint} gives no results",
            )
            return res["results"]["bindings"]
        except Exception:
            self.fail(
                msg=f"Error running the federated query to {self.blazegraph_endpoint}: {resp.text}",
            )

        # NOTE: test using oxigraph as backend
        # g = Graph(store="Oxigraph")
        # app = SparqlEndpoint(graph=g)
        # endpoint = TestClient(app)
        # response = endpoint.get(
        #     "/?query=" + urllib.parse.quote(FEDERATED_QUERY), headers={"accept": "application/json"}
        # )
        # print(response.json()["results"]["bindings"])
        # assert response.status_code == 200
        # assert len(response.json()["results"]["bindings"]) > 0
