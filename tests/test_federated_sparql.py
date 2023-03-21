# -*- coding: utf-8 -*-
"""Tests federated SPARQL queries to an identifier mapping service deployed publicly."""

import unittest
import urllib.parse

import requests

# tox -- tests/test_federated_sparql.py -s
# pytest tests/test_federated_sparql.py -s
# TODO: we might want to add checks if the endpoints are up, and skip the test if not up

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

    def test_federated_virtuoso(self):
        """Test sending a federated query to a public mapping service from Virtuoso."""
        try:
            resp = requests.get(VIRTUOSO_ENDPOINT,
                params={"query": FEDERATED_QUERY},
                headers={"accept": "application/json"}
            )
            res = resp.json()
            self.assertGreater(len(res["results"]["bindings"]), 0, msg="Federated Virtuoso no results")
        except Exception:
            self.assertTrue(False, msg=f"Error running the federated query to Virtuoso: {resp.text}")


    def test_federated_blazegraph(self):
        """Test sending a federated query to a public mapping service from Blazegraph"""
        try:
            resp = requests.get(BLAZEGRAPH_ENDPOINT,
                params={"query": FEDERATED_QUERY},
                headers={"accept": "application/json"}
            )
            res = resp.json()
            self.assertGreater(len(res["results"]["bindings"]), 0, msg="Federated blazegraph no results")
        except Exception:
            self.assertTrue(False, msg=f"Error running the federated query to blazegraph: {resp.text}")


    def test_federated_graphdb(self):
        """Test sending a federated query to a public mapping service from GraphDB."""
        try:
            resp = requests.get(GRAPHDB_ENDPOINT,
                params={"query": FEDERATED_QUERY},
                headers={"accept": "application/json"}
            )
            res = resp.json()
            self.assertGreater(len(res["results"]["bindings"]), 0, msg="Federated GraphDB no results")
        except Exception:
            self.assertTrue(False, msg=f"Error running the federated query to GraphDB: {resp.text}")
