# -*- coding: utf-8 -*-

"""Tests for the simple web service."""

import unittest
from typing import ClassVar

from fastapi.testclient import TestClient

from curies import Converter
from curies.web import FAILURE_CODE, get_fastapi_app, get_flask_app


class ConverterMixin(unittest.TestCase):
    """A mixin that has a converter."""

    delimiter: ClassVar[str] = ":"

    def setUp(self) -> None:
        """Set up the test case with a converter."""
        super().setUp()
        self.converter = Converter.from_prefix_map(
            {
                "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
                "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
                "GO": "http://purl.obolibrary.org/obo/GO_",
                "OBO": "http://purl.obolibrary.org/obo/",
            },
            delimiter=self.delimiter,
        )


class TestFastAPI(ConverterMixin):
    """Test building a simple web service with FastAPI."""

    def setUp(self) -> None:
        """Set up the test case with a converter, blueprint, and app."""
        super().setUp()
        self.app = get_fastapi_app(self.converter)
        self.client = TestClient(self.app)

    def test_resolve_success(self):
        """Test resolution for a valid CURIE redirects properly."""
        curie = self.converter.format_curie("GO", "1234567")
        res = self.client.get(f"/{curie}", follow_redirects=False)
        self.assertEqual(302, res.status_code, msg=res.text)

    def test_resolve_failure(self):
        """Test resolution for an invalid CURIE aborts with 404."""
        curie = self.converter.format_curie("NOPREFIX", "NOIDENTIFIER")
        res = self.client.get(f"/{curie}", follow_redirects=False)
        self.assertEqual(FAILURE_CODE, res.status_code, msg=res.text)


class TestFastAPISlashed(TestFastAPI):
    """Test the FastAPI router with an alternate delimiter."""

    delimiter = "/"

    def test_delimiter(self):
        """Test the delimiter."""
        self.assertEqual("/", self.converter.delimiter)


class TestFlaskBlueprint(ConverterMixin):
    """Test building a simple web service with Flask."""

    def setUp(self) -> None:
        """Set up the test case with a converter, blueprint, and app."""
        super().setUp()
        self.app = get_flask_app(self.converter)

    def test_resolve_success(self):
        """Test resolution for a valid CURIE redirects properly."""
        curie = self.converter.format_curie("GO", "1234567")
        with self.app.test_client() as client:
            res = client.get(f"/{curie}", follow_redirects=False)
            self.assertEqual(302, res.status_code, msg=res.text)

    def test_resolve_failure(self):
        """Test resolution for an invalid CURIE aborts with 404."""
        curie = self.converter.format_curie("NOPREFIX", "NOIDENTIFIER")
        with self.app.test_client() as client:
            res = client.get(f"/{curie}", follow_redirects=False)
            self.assertEqual(FAILURE_CODE, res.status_code, msg=res.text)


class TestFlaskBlueprintSlashed(TestFlaskBlueprint):
    """Test the flask blueprint with an alternate delimiter."""

    delimiter = "/"

    def test_delimiter(self):
        """Test the delimiter."""
        self.assertEqual("/", self.converter.delimiter)
