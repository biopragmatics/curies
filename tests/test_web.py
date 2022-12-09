# -*- coding: utf-8 -*-

"""Tests for the simple web service."""

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from flask import Flask

from curies import Converter
from curies.web import FAILURE_CODE, get_fastapi_router, get_flask_blueprint


class TestWebMixin(unittest.TestCase):
    def setUp(self) -> None:
        """Set up the test case with a converter, blueprint, and app."""
        super().setUp()
        self.converter = Converter.from_prefix_map(
            {
                "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
                "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
                "GO": "http://purl.obolibrary.org/obo/GO_",
                "OBO": "http://purl.obolibrary.org/obo/",
            }
        )


class TestFastAPI(TestWebMixin):
    """Test building a simple web service with FastAPI."""

    def setUp(self) -> None:
        """Set up the test case with a converter, blueprint, and app."""
        super().setUp()
        self.app = FastAPI()
        self.client = TestClient(self.app)
        self.router = get_fastapi_router(self.converter)
        self.app.include_router(self.router)

    def test_resolve_success(self):
        """Test resolution for a valid CURIE redirects properly."""
        res = self.client.get("GO:1234567", allow_redirects=False)
        self.assertEqual(302, res.status_code, msg=res.text)


class TestFlaskBlueprint(TestWebMixin):
    """Test building a simple web service with Flask."""

    def setUp(self) -> None:
        """Set up the test case with a converter, blueprint, and app."""
        super().setUp()
        self.blueprint = get_flask_blueprint(self.converter)
        self.app = Flask(__name__)
        self.app.register_blueprint(self.blueprint)

    def test_resolve_success(self):
        """Test resolution for a valid CURIE redirects properly."""
        with self.app.test_client() as client:
            res = client.get("/GO:1234567", follow_redirects=False)
            self.assertEqual(302, res.status_code, msg=res.text)

    def test_resolve_failure(self):
        """Test resolution for an invalid CURIE aborts with 404."""
        with self.app.test_client() as client:
            res = client.get("/NOPREFIX:NOIDENTIFIER", follow_redirects=False)
            self.assertEqual(FAILURE_CODE, res.status_code, msg=res.text)
