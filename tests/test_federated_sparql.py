# -*- coding: utf-8 -*-
"""Tests federated SPARQL queries to an identifier mapping service deployed publicly.
TODO: we might want to add checks if the endpoints are up, and skip the test if not up
"""

import unittest

import requests

MAPPING_ENDPOINT = "https://bioregistry.io/sparql"
GRAPHDB_ENDPOINT = "https://graphdb.dumontierlab.com/repositories/test"
VIRTUOSO_ENDPOINT = "https://bio2rdf.org/sparql"
BLAZEGRAPH_ENDPOINT = "http://kg-hub-rdf.berkeleybop.io/blazegraph/sparql"

FEDERATED_QUERY = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?o WHERE {{
    SERVICE <{MAPPING_ENDPOINT}> {{
        <http://purl.obolibrary.org/obo/CHEBI_24867> owl:sameAs ?o
    }}
}}"""

# NOTE: Keeping temporarily to check querying works properly
# FEDERATED_QUERY = """PREFIX owl: <http://www.w3.org/2002/07/owl#>
# SELECT DISTINCT ?o WHERE {
#     ?s ?p ?o .
# } LIMIT 100"""


class TestFederatedSparql(unittest.TestCase):
    """Test the identifier mapping service."""

    def query_endpoint(self, endpoint, query):
        try:
            resp = requests.get(
                endpoint,
                params={"query": query},
                headers={"accept": "application/json"},
            )
            res = resp.json()
            self.assertGreater(
                len(res["results"]["bindings"]), 0, msg=f"Federated query to {endpoint} gives no results"
            )
            return res["results"]["bindings"]
        except Exception:
            self.assertTrue(
                False, msg=f"Error running the federated query to {endpoint}: {resp.text}"
            )
        return None


    def test_federated_virtuoso(self):
        """Test sending a federated query to a public mapping service from Virtuoso."""
        self.query_endpoint(VIRTUOSO_ENDPOINT, FEDERATED_QUERY)

    def test_federated_blazegraph(self):
        """Test sending a federated query to a public mapping service from Blazegraph"""
        self.query_endpoint(BLAZEGRAPH_ENDPOINT, FEDERATED_QUERY)

    def test_federated_graphdb(self):
        """Test sending a federated query to a public mapping service from GraphDB."""
        self.query_endpoint(GRAPHDB_ENDPOINT, FEDERATED_QUERY)