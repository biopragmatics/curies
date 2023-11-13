"""Test discovering a prefix map from a list of URIs."""

import unittest
from typing import ClassVar

import rdflib

from curies import Converter, Record
from curies.discovery import discover, discover_from_rdf


class TestDiscovery(unittest.TestCase):
    """Test discovery of URI prefixes."""

    converter: ClassVar[Converter]

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test case with a dummy converter."""
        cls.converter = Converter(
            [Record(prefix="GO", uri_prefix="http://purl.obolibrary.org/obo/GO_")]
        )

    def test_simple(self):
        """Test a simple case of discovering URI prefixes."""
        uris = [f"http://ran.dom/{i:03}" for i in range(30)]
        uris.append("http://purl.obolibrary.org/obo/GO_0001234")

        converter = discover(self.converter, uris, cutoff=3)
        self.assertEqual([Record(prefix="ns1", uri_prefix="http://ran.dom/")], converter.records)
        self.assertEqual("ns1:001", converter.compress("http://ran.dom/001"))
        self.assertIsNone(
            converter.compress("http://purl.obolibrary.org/obo/GO_0001234"),
            msg="discovered converter should not inherit reference converter's definitions",
        )

        converter = discover(self.converter, uris, cutoff=50)
        self.assertEqual([], converter.records)
        self.assertIsNone(
            converter.compress("http://ran.dom/001"),
            msg="cutoff was high, so discovered converter should not detect `http://ran.dom/`",
        )

    def test_rdflib(self):
        """Test discovery in RDFlib."""
        graph = rdflib.Graph()
        for i in range(30):
            graph.add(
                (
                    rdflib.URIRef(f"http://ran.dom/{i:03}"),
                    rdflib.RDFS.subClassOf,
                    rdflib.URIRef(f"http://ran.dom/{i + 1:03}"),
                )
            )
            graph.add(
                (
                    rdflib.URIRef(f"http://ran.dom/{i:03}"),
                    rdflib.RDFS.label,
                    rdflib.Literal(f"Node {i}"),
                )
            )

        converter = discover_from_rdf(self.converter, graph)
        self.assertEqual([Record(prefix="ns1", uri_prefix="http://ran.dom/")], converter.records)
        self.assertEqual("ns1:001", converter.compress("http://ran.dom/001"))
        self.assertIsNone(
            converter.compress("http://purl.obolibrary.org/obo/GO_0001234"),
            msg="discovered converter should not inherit reference converter's definitions",
        )
