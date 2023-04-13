# -*- coding: utf-8 -*-

"""Identifier mappings service.

This contains an implementation of the service described in `SPARQL-enabled identifier
conversion with Identifiers.org <https://pubmed.ncbi.nlm.nih.gov/25638809/>`_.
The idea here is that you can write a SPARQL query like the following:

.. code-block:: sparql

    PREFIX biomodel: <http://identifiers.org/biomodels.db/>
    PREFIX bqbio: <http://biomodels.net/biology-qualifiers#>
    PREFIX sbmlrdf: <http://identifiers.org/biomodels.vocabulary#>
    PREFIX up: <http://purl.uniprot.org/core/>

    SELECT DISTINCT ?protein ?protein_domain
    WHERE {
        # The first part of this query extracts the proteins appearing in an RDF serialization
        # of the BioModels database (see https://www.ebi.ac.uk/biomodels/BIOMD0000000372) on
        # insulin/glucose feedback. Note that modelers call entities appearing in compartmental
        # models "species", and this does not refer to taxa.
        biomodel:BIOMD0000000372 sbmlrdf:species/bqbio:isVersionOf ?biomodels_protein .

        # The second part of this query maps BioModels protein IRIs to UniProt protein IRIs
        # using service XXX - that's what we're implementing here.
        SERVICE <XXX> {
            ?biomodels_protein owl:sameAs ?uniprot_protein.
        }

        # The third part of this query gets links between UniProt proteins and their
        # domains. Since the service maps between the BioModels query, this only gets
        # us relevant protein domains to the insulin/glucose model.
        SERVICE <http://beta.sparql.uniprot.org/sparql> {
            ?uniprot_protein a up:Protein;
                up:organism taxon:9606;
                rdfs:seeAlso ?protein_domain.
        }
    }

The SPARQL endpoint running at the web address XXX takes in the bound values for `?biomodels_protein`
one at a time and dynamically generates triples with `owl:sameAs` as the predicate mapping and other
equivalent IRIs (based on the definition of the converter) as the objects. This allows for gluing
together multiple services that use different URIs for the same entities - in this example, there
are two ways of referring to UniProt Proteins:

1. The BioModels database example represents a SBML model on insulin-glucose feedback and uses legacy
   Identifiers.org URIs for proteins such as http://identifiers.org/uniprot/P01308.
2. The first-part UniProt database uses its own PURLs such as https://purl.uniprot.org/uniprot/P01308.

.. seealso::

    - Jerven Bolleman's implementation of this service in Java: https://github.com/JervenBolleman/sparql-identifiers
    - Vincent Emonet's `SPARQL endpoint for RDFLib generator <https://github.com/vemonet/rdflib-endpoint>`_

The following is an end-to-end example of using this function to create
a small URI mapping application.

.. code-block::

    # flask_example.py
    from flask import Flask
    from curies import Converter, get_bioregistry_converter
    from curies.mapping_service import get_flask_mapping_app

    # Create a converter
    converter: Converter = get_bioregistry_converter()

    # Create the Flask app from the converter
    app: Flask = get_flask_mapping_app(converter)

    if __name__ == "__main__":
        app.run()

In the command line, either run your Python file directly, or via with :mod:`gunicorn`:

.. code-block:: shell

    pip install gunicorn
    gunicorn --bind 0.0.0.0:8764 flask_example:app

Test a request in the Python REPL.

.. code-block::

    import requests
    sparql = '''
        SELECT ?s ?o WHERE {
            VALUES ?s { <http://purl.obolibrary.org/obo/CHEBI_2> }
            ?s owl:sameAs ?o
        }
    '''
    >>> res = requests.get("http://localhost:8764/sparql", params={"query": sparql})

Test a request using a service, e.g. with :meth:`rdflib.Graph.query`

.. code-block:: sparql

    SELECT ?s ?o WHERE {
        VALUES ?s { <http://purl.obolibrary.org/obo/CHEBI_2> }
        SERVICE <http://localhost:8764/sparql> {
            ?s owl:sameAs ?child_mapped .
        }
    }
"""

from .api import (
    MappingServiceGraph,
    get_fastapi_mapping_app,
    get_fastapi_router,
    get_flask_mapping_app,
    get_flask_mapping_blueprint,
)
from .rdflib_custom import MappingServiceSPARQLProcessor  # type:ignore

__all__ = [
    "MappingServiceGraph",
    "MappingServiceSPARQLProcessor",
    "get_flask_mapping_blueprint",
    "get_flask_mapping_app",
    "get_fastapi_router",
    "get_fastapi_mapping_app",
]
