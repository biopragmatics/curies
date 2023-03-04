# -*- coding: utf-8 -*-

"""Tests for the identifier mapping service."""

import unittest

from rdflib import OWL, SKOS

from curies import Converter
from curies.mapping_service import CURIEServiceGraph, _prepare_predicates


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

    def test_prepare_predicates(self):
        """Test preparation of predicates."""
        self.assertEqual({OWL.sameAs}, _prepare_predicates())
        self.assertEqual({OWL.sameAs}, _prepare_predicates(OWL.sameAs))
        self.assertEqual(
            {OWL.sameAs, SKOS.exactMatch}, _prepare_predicates({OWL.sameAs, SKOS.exactMatch})
        )

    def test_errors(self):
        """Test errors."""
        for sparql in [
            # errors because of unbound subject
            "SELECT ?s ?o WHERE { ?s owl:sameAs ?o }",
            # errors because of bad predicate
            "SELECT ?o WHERE { <http://purl.obolibrary.org/obo/CHEBI_1> rdfs:seeAlso ?o }",
            # errors because predicate is given
            "SELECT * WHERE { <http://purl.obolibrary.org/obo/CHEBI_1> "
            "?rdfs:seeAlso <http://purl.obolibrary.org/obo/CHEBI_1> }",
        ]:
            with self.subTest(sparql=sparql), self.assertRaises(Exception):
                list(self.graph.query(sparql))

    def test_sparql(self):
        """Test a sparql query on the graph."""
        sparql = """\
            SELECT DISTINCT ?s ?o WHERE {
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

    def test_missing(self):
        """Test a sparql query on the graph where the URIs can't be parsed."""
        sparql = """\
            SELECT ?s ?o WHERE {
                VALUES ?s { <http://example.org/1> <http://example.org/1> }
                ?s owl:sameAs ?o
            }
        """
        self.assertEqual([], list(self.graph.query(sparql)))
