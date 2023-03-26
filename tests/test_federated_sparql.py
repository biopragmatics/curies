# -*- coding: utf-8 -*-

"""Tests federated SPARQL queries to an identifier mapping service deployed publicly.

TODO: we might want to add checks if the endpoints are up, and skip the test if not up
"""

import time
import unittest
from multiprocessing import Process
from typing import ClassVar, Set, Tuple

import requests
import uvicorn

from curies import Converter
from curies.mapping_service import _handle_header, get_fastapi_mapping_app
from curies.mapping_service.utils import CONTENT_TYPE_TO_HANDLER
from tests.test_mapping_service import PREFIX_MAP

BLAZEGRAPH_ENDPOINT = "http://localhost:9999/blazegraph/namespace/kb/sparql"
BLAZEGRAPH_JAR_URL = (
    "https://github.com/blazegraph/database/releases/download/BLAZEGRAPH_2_1_6_RC/blazegraph.jar"
)
PING_SPARQL = 'SELECT ?s ?o WHERE { BIND("hello" as ?s) . BIND("there" as ?o) . }'
SPARQL_FMT = """\
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?s ?o WHERE {{
    SERVICE <{mapping_service}> {{
        VALUES ?s {{ <http://purl.obolibrary.org/obo/CHEBI_24867> }}
        ?s owl:sameAs ?o
    }}
}}
""".rstrip()


def get(endpoint: str, sparql: str, accept: str):
    """Get a response from a given SPARQL query."""
    res = requests.get(
        endpoint,
        params={"query": sparql},
        headers={"accept": accept},
    )
    func = CONTENT_TYPE_TO_HANDLER[_handle_header(accept)]
    return func(res.text)


def _get_so(records) -> Set[Tuple[str, str]]:
    return {(record["s"], record["o"]) for record in records}


def sparql_service_available(endpoint: str) -> bool:
    """Test if a SPARQL service is running."""
    try:
        records = get(endpoint, PING_SPARQL, "application/json")
    except requests.exceptions.ConnectionError:
        return False
    return {("hello", "there")} == _get_so(records)


class FederationMixin(unittest.TestCase):
    """A shared mixin for testing."""

    def assert_service_works(self, endpoint: str):
        """Assert that a service is able to accept a simple SPARQL query."""
        records = get(endpoint, PING_SPARQL, accept="application/json")
        self.assertEqual(1, len(records))
        self.assertEqual("hello", records[0]["s"])
        self.assertEqual("there", records[0]["o"])


def _get_app():
    converter = Converter.from_priority_prefix_map(PREFIX_MAP)
    app = get_fastapi_mapping_app(converter)
    return app


@unittest.skipUnless(
    sparql_service_available(BLAZEGRAPH_ENDPOINT), reason="Blazegraph is not running"
)
class TestFederatedSparql(FederationMixin):
    """Test the identifier mapping service."""

    endpoint: ClassVar[str] = BLAZEGRAPH_ENDPOINT
    mapping_service_process: Process

    def setUp(self):
        """Set up the test case."""
        # Start the curies mapping service SPARQL endpoint
        self.mapping_service_process = Process(
            target=uvicorn.run,
            # uvicorn.run accepts a zero-argument callable that returns an app
            args=(_get_app,),
            # kwargs={"host": "localhost", "port": 8000, "log_level": "info"},
            daemon=True,
        )
        self.mapping_service_process.start()
        time.sleep(5)

        self.mapping_service = "http://localhost:8000/sparql"  # TODO get from app/configure app
        self.sparql = SPARQL_FMT.format(mapping_service=self.mapping_service)

        self.assert_service_works(self.mapping_service)

    def tearDown(self):
        """Tear down the testing case."""
        self.mapping_service_process.kill()

    def test_federated_local(self):
        """Test sending a federated query to a local mapping service from a local service."""
        for mimetype in CONTENT_TYPE_TO_HANDLER:
            with self.subTest(mimetype=mimetype):
                records = get(self.endpoint, self.sparql, accept=mimetype)
                self.assertIn(
                    (
                        "http://purl.obolibrary.org/obo/CHEBI_24867",
                        "http://identifiers.org/chebi/24867",
                    ),
                    _get_so(records),
                )
