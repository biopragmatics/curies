# -*- coding: utf-8 -*-

"""Tests federated SPARQL queries to an identifier mapping service deployed publicly.

TODO: we might want to add checks if the endpoints are up, and skip the test if not up
"""

import os
import subprocess
import time
import unittest
from multiprocessing import Process

import pystow
import requests
import uvicorn

from curies import Converter
from curies.mapping_service import get_fastapi_mapping_app
from tests.test_mapping_service import PREFIX_MAP

BIOREGISTRY_SPARQL_ENDPOINT = "https://bioregistry.io/sparql"
TEST_QUERY = 'SELECT ?test WHERE { BIND("hello" as ?test) }'


class TestPublicFederatedSparql(unittest.TestCase):
    """Test the identifier mapping service."""

    def setUp(self) -> None:
        self.sparql = f"""\
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT DISTINCT ?o WHERE {{
            SERVICE <{BIOREGISTRY_SPARQL_ENDPOINT}> {{
                <http://purl.obolibrary.org/obo/CHEBI_24867> owl:sameAs ?o
            }}
        }}
        """.rstrip()

    def query_endpoint(self, endpoint: str, query: str):
        """Query an endpoint."""
        # TODO assert that the endpoint is up and running before
        #  trying to test the service
        try:
            resp = requests.get(
                endpoint,
                params={"query": query},
                headers={"accept": "application/json"},
            )
            res = resp.json()
            self.assertGreater(
                len(res["results"]["bindings"]),
                0,
                msg=f"Federated query to {endpoint} gives no results",
            )
            return res["results"]["bindings"]
        except Exception:
            self.fail(msg=f"Error running the federated query to {endpoint}: {resp.text}")

    def test_public_federated_virtuoso(self):
        """Test sending a federated query to a public mapping service from Virtuoso."""
        self.query_endpoint("https://bio2rdf.org/sparql", self.sparql)

    def test_public_federated_blazegraph(self):
        """Test sending a federated query to a public mapping service from Blazegraph"""
        self.query_endpoint("http://kg-hub-rdf.berkeleybop.io/blazegraph/sparql", self.sparql)

    def test_public_federated_graphdb(self):
        """Test sending a federated query to a public mapping service from GraphDB."""
        self.query_endpoint("https://graphdb.dumontierlab.com/repositories/test", self.sparql)


def _get_app():
    converter = Converter.from_priority_prefix_map(PREFIX_MAP)
    app = get_fastapi_mapping_app(converter)
    return app


class TestFederatedSparql(unittest.TestCase):
    """Test the identifier mapping service."""

    proc: Process
    proc_blazegraph: Process

    def get(self, sparql: str, accept: str = "application/json") -> requests.Response:
        """Get a response from a given SPARQL query."""
        return requests.get(
            self.blazegraph_endpoint,
            params={"query": sparql},
            headers={"accept": accept},
        )

    def assert_blazegraph_running(self):
        """Check that blazegraph is running properly."""
        try:
            res = self.get(TEST_QUERY)
        except requests.exceptions.ConnectionError:
            return self.fail("blazegraph is not running")
        res_json = res.json()
        self.assertIn("results", res_json)
        self.assertIn("bindings", res_json["results"])
        self.assertEqual(1, len(res_json["results"]["bindings"]))
        self.assertIn("test", res_json["results"]["bindings"][0])
        self.assertIn("value", res_json["results"]["bindings"][0]["test"])
        self.assertEqual("hello", res_json["results"]["bindings"][0]["test"]["value"])

    def setUp(self):
        """Set up the test case."""
        self.blazegraph_jar_path = pystow.ensure(
            "blazegraph",
            url="https://github.com/blazegraph/database/releases/download/BLAZEGRAPH_2_1_6_RC/blazegraph.jar",
        )
        self.blazegraph_port = 9999
        # maybe check setting port https://github.com/blazegraph/database/wiki/NanoSparqlServer#changing-the-default-port
        # f"-Djetty.port={self.blazegraph_port}"
        self.blazegraph_endpoint = (
            f"http://localhost:{self.blazegraph_port}/blazegraph/namespace/kb/sparql"
        )

        try:
            self.get(TEST_QUERY)
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
        resp = self.get(self.sparql)
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
        # response = endpoint.get("/?query=" + urllib.parse.quote(FEDERATED_QUERY), headers={"accept": "application/json"})
        # print(response.json()["results"]["bindings"])
        # assert response.status_code == 200
        # assert len(response.json()["results"]["bindings"]) > 0
