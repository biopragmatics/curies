"""Tests federated SPARQL queries between the curies mapping service and popular triplestores."""

import time
from multiprocessing import Process
from typing import ClassVar

import uvicorn

from curies import Converter
from curies.mapping_service import get_fastapi_mapping_app
from curies.mapping_service.utils import sparql_service_available
from tests import cases
from tests.test_mapping_service import PREFIX_MAP


class TestDockerFederation(cases.FederationMixin):
    """Tests federated SPARQL queries between the curies mapping service and blazegraph/virtuoso triplestores.

    Run and init the required triplestores locally:
    1. docker compose up
    2. ./tests/resources/init_triplestores.sh
    """

    def setUp(self) -> None:
        """Set up the test case."""
        self.mapping_service = cases.LOCAL_MAPPING_SERVICE

        if not sparql_service_available(self.mapping_service):
            self.skipTest(f"Mapping service is not available: {self.mapping_service}")


def _get_app():
    converter = Converter.from_priority_prefix_map(PREFIX_MAP)
    app = get_fastapi_mapping_app(converter)
    return app


class TestLocalFederation(cases.FederationMixin):
    """Tests federated SPARQL queries."""

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

        if not sparql_service_available(self.mapping_service):
            self.skipTest(f"Mapping service is not available: {self.mapping_service}")
