# -*- coding: utf-8 -*-

"""Tests for the identifier mapping service."""

import unittest

from curies import Converter
from curies.mapping_service import CURIEServiceGraph


class TestMappingService(unittest.TestCase):
    """Test the identifier mapping service."""

    def setUp(self) -> None:
        """Set up the converter."""
        self.converter = Converter.from_priority_prefix_map(
            {
                "CHEBI": [
                    "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=",
                    "http://identifiers.org/chebi/",
                    "http://purl.obolibrary.org/obo/CHEBI_",
                ],
                "GO": ["http://purl.obolibrary.org/obo/GO_"],
                "OBO": ["http://purl.obolibrary.org/obo/"],
            }
        )
        self.graph = CURIEServiceGraph(converter=self.converter)

    def test_errors(self):
        """Test errors."""
        for sparql in [
            "SELECT ?s ?p ?o WHERE { ?s ?p ?o }",
        ]:
            with self.subTest(sparql=sparql):
                with self.assertRaises(ValueError):
                    self.graph.query(sparql)

    def test_sparql(self):
        """Test a sparql query on the graph."""
        sparql = """\
            SELECT DISTINCT ?s ?o
            WHERE {
                VALUES ?s {
                    <http://purl.obolibrary.org/obo/CHEBI_1>
                    <http://purl.obolibrary.org/obo/CHEBI_2>
                }
                ?s owl:sameAs ?o
            }
            """
        rows = {tuple(map(str, row)) for row in self.graph.query(sparql)}
        self.assertEqual(
            {
                (
                    "http://purl.obolibrary.org/obo/CHEBI_1",
                    "http://purl.obolibrary.org/obo/CHEBI_1",
                ),
                ("http://purl.obolibrary.org/obo/CHEBI_1", "http://identifiers.org/chebi/1"),
                (
                    "http://purl.obolibrary.org/obo/CHEBI_1",
                    "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=1",
                ),
                (
                    "http://purl.obolibrary.org/obo/CHEBI_2",
                    "http://purl.obolibrary.org/obo/CHEBI_2",
                ),
                ("http://purl.obolibrary.org/obo/CHEBI_2", "http://identifiers.org/chebi/2"),
                (
                    "http://purl.obolibrary.org/obo/CHEBI_2",
                    "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=2",
                ),
            },
            rows,
        )
