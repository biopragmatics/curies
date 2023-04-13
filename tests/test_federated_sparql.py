# -*- coding: utf-8 -*-

"""Tests federated SPARQL queries with a locally deployed triple store."""

import time
import unittest
from multiprocessing import Process
from typing import ClassVar

import uvicorn

from curies import Converter
from curies.mapping_service import get_fastapi_mapping_app
from curies.mapping_service.utils import (
    get_sparql_record_so_tuples,
    get_sparql_records,
    sparql_service_available,
)
from tests.test_mapping_service import PREFIX_MAP

BLAZEGRAPH_ENDPOINT = "http://localhost:9999/blazegraph/namespace/kb/sparql"
BLAZEGRAPH_JAR_URL = (
    "https://github.com/blazegraph/database/releases/download/BLAZEGRAPH_2_1_6_RC/blazegraph.jar"
)
SPARQL_FMT = """\
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?s ?o WHERE {{
    SERVICE <{mapping_service}> {{
        VALUES ?s {{ <http://purl.obolibrary.org/obo/CHEBI_24867> }}
        ?s owl:sameAs ?o
    }}
}}
""".rstrip()


class FederationMixin(unittest.TestCase):
    """A shared mixin for testing."""

    def assert_service_works(self, endpoint: str):
        """Assert that a service is able to accept a simple SPARQL query."""
        self.assertTrue(sparql_service_available(endpoint))


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
    host: ClassVar[str] = "localhost"
    port: ClassVar[int] = 8000
    mapping_service_process: Process

    def setUp(self):
        """Set up the test case."""
        # Start the curies mapping service SPARQL endpoint
        self.mapping_service_process = Process(
            target=uvicorn.run,
            # uvicorn.run accepts a zero-argument callable that returns an app
            args=(_get_app,),
            kwargs={"host": self.host, "port": self.port, "log_level": "info"},
            daemon=True,
        )
        self.mapping_service_process.start()
        time.sleep(5)

        self.mapping_service = f"http://{self.host}:{self.port}/sparql"
        self.sparql = SPARQL_FMT.format(mapping_service=self.mapping_service)

        self.assert_service_works(self.mapping_service)

    def tearDown(self):
        """Tear down the testing case."""
        self.mapping_service_process.kill()

    def test_federated_local(self):
        """Test sending a federated query to a local mapping service from a local service."""
        for mimetype in [
            "application/sparql-results+json",
            "application/sparql-results+xml",
            "text/csv",  # for some reason, Blazegraph wants this instead of application/sparql-results+csv
        ]:
            with self.subTest(mimetype=mimetype):
                records = get_sparql_records(self.endpoint, self.sparql, accept=mimetype)
                self.assertIn(
                    (
                        "http://purl.obolibrary.org/obo/CHEBI_24867",
                        "http://identifiers.org/chebi/24867",
                    ),
                    get_sparql_record_so_tuples(records),
                )
