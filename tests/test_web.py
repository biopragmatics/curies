# -*- coding: utf-8 -*-

"""Tests for the simple web service."""

import unittest

from flask import Flask

from curies import Converter
from curies.web import FAILURE_CODE, get_blueprint


class TestBlueprint(unittest.TestCase):
    """Test building a simple web service."""

    def setUp(self) -> None:
        """Set up the test case with a converter, blueprint, and app."""
        self.converter = Converter.from_prefix_map(
            {
                "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
                "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
                "GO": "http://purl.obolibrary.org/obo/GO_",
                "OBO": "http://purl.obolibrary.org/obo/",
            }
        )
        self.blueprint = get_blueprint(self.converter)
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
