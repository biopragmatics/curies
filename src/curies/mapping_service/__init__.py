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

import itertools as itt
from typing import TYPE_CHECKING, Any, Collection, Iterable, List, Optional, Set, Tuple, Union, cast

from rdflib import OWL, Graph, URIRef
from rdflib.term import _is_valid_uri

from .rdflib_custom import MappingServiceSPARQLProcessor  # type: ignore
from ..api import Converter

if TYPE_CHECKING:
    import fastapi
    import flask

__all__ = [
    "MappingServiceGraph",
    "MappingServiceSPARQLProcessor",
    "get_flask_mapping_blueprint",
    "get_flask_mapping_app",
    "get_fastapi_router",
    "get_fastapi_mapping_app",
]


def _prepare_predicates(predicates: Union[None, str, Collection[str]] = None) -> Set[URIRef]:
    if predicates is None:
        return {OWL.sameAs}
    if isinstance(predicates, str):
        return {URIRef(predicates)}
    return {URIRef(predicate) for predicate in predicates}


class MappingServiceGraph(Graph):  # type:ignore
    """A service that implements identifier mapping based on a converter."""

    converter: Converter
    predicates: Set[URIRef]

    def __init__(
        self,
        *args: Any,
        converter: Converter,
        predicates: Union[None, str, List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Instantiate the graph.

        :param args: Positional arguments to pass to :meth:`rdflib.Graph.__init__`
        :param converter: A converter object
        :param predicates: A predicate or set of predicates. If not given, this service
            will use `owl:sameAs` as a predicate for mapping IRIs.
        :param kwargs: Keyword arguments to pass to :meth:`rdflib.Graph.__init__`

        In the following example, a service graph is instantiated using a small example
        converter, then an example SPARQL query is made directly to show how it makes
        results:

        .. code-block:: python

            from curies import Converter
            from curies.mapping_service import CURIEServiceGraph

            converter = Converter.from_priority_prefix_map(
                {
                    "CHEBI": [
                        "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=",
                        "http://identifiers.org/chebi/",
                        "http://purl.obolibrary.org/obo/CHEBI_",
                    ],
                    "GO": ["http://purl.obolibrary.org/obo/GO_"],
                    "OBO": ["http://purl.obolibrary.org/obo/"],
                    ...,
                }
            )
            graph = CURIEServiceGraph(converter=converter)

            res = graph.query('''
                SELECT ?o WHERE {
                    VALUES ?s {
                        <http://purl.obolibrary.org/obo/CHEBI_1>
                    }
                    ?s owl:sameAs ?o
                }
            ''')


        The results of this are:

        ======================================  =================================================
        subject                                 object
        --------------------------------------  -------------------------------------------------
        http://purl.obolibrary.org/obo/CHEBI_1  http://purl.obolibrary.org/obo/CHEBI_1
        http://purl.obolibrary.org/obo/CHEBI_1  http://identifiers.org/chebi/1
        http://purl.obolibrary.org/obo/CHEBI_1  https://www.ebi.ac.uk/chebi/searchId.do?chebiId=1
        ======================================  =================================================
        """
        self.converter = converter
        self.predicates = _prepare_predicates(predicates)
        super().__init__(*args, **kwargs)

    def _expand_pair_all(self, uri_in: str) -> List[URIRef]:
        prefix, identifier = self.converter.parse_uri(uri_in)
        if prefix is None or identifier is None:
            return []
        uris = cast(Collection[str], self.converter.expand_pair_all(prefix, identifier))
        # do _is_valid_uri check because some configurations e.g. from Bioregistry might
        # produce invalid URIs e.g., containing spaces
        return [URIRef(uri) for uri in uris if _is_valid_uri(uri)]

    def triples(
        self, triple: Tuple[URIRef, URIRef, URIRef]
    ) -> Iterable[Tuple[URIRef, URIRef, URIRef]]:
        """Generate triples, overriden to dynamically generate mappings based on this graph's converter."""
        subj_query, pred_query, obj_query = triple
        if pred_query in self.predicates:
            if subj_query is None and obj_query is not None:
                subjects = self._expand_pair_all(obj_query)
                for subj, pred in itt.product(subjects, self.predicates):
                    yield subj, pred, obj_query
            elif subj_query is not None and obj_query is None:
                objects = self._expand_pair_all(subj_query)
                for obj, pred in itt.product(objects, self.predicates):
                    yield subj_query, pred, obj


#: This is default for federated queries
DEFAULT_CONTENT_TYPE = "application/sparql-results+xml"

#: A mapping from content types to the keys used for serializing
#: in :meth:`rdflib.Graph.serialize` and other serialization functions
CONTENT_TYPE_TO_RDFLIB_FORMAT = {
    # https://www.w3.org/TR/sparql11-results-json/
    "application/sparql-results+json": "json",
    "application/json": "json",
    "text/json": "json",
    # https://www.w3.org/TR/rdf-sparql-XMLres/
    "application/sparql-results+xml": "xml",
    "application/xml": "xml",  # for compatibility
    "text/xml": "xml",  # not standard
    # https://www.w3.org/TR/sparql11-results-csv-tsv/
    "application/sparql-results+csv": "csv",
    "text/csv": "csv",  # for compatibility
    # TODO other direct RDF serializations
    # "text/turtle": "ttl",
    # "text/n3": "n3",
    # "application/ld+json": "json-ld",
}


def _handle_header(header: Optional[str]) -> str:
    if not header or header == "*/*":
        return DEFAULT_CONTENT_TYPE
    return header


def get_flask_mapping_blueprint(
    converter: Converter, route: str = "/sparql", **kwargs: Any
) -> "flask.Blueprint":
    """Get a blueprint for :class:`flask.Flask`.

    :param converter: A converter
    :param route: The route of the SPARQL service (relative to the base of the Blueprint)
    :param kwargs: Keyword arguments passed through to :class:`flask.Blueprint`
    :return: A blueprint
    """
    from flask import Blueprint, Response, request

    blueprint = Blueprint("mapping", __name__, **kwargs)
    graph = MappingServiceGraph(converter=converter)
    processor = MappingServiceSPARQLProcessor(graph=graph)

    @blueprint.route(route, methods=["GET", "POST"])  # type:ignore
    def serve_sparql() -> "Response":
        """Run a SPARQL query and serve the results."""
        sparql = (request.args if request.method == "GET" else request.json).get("query")
        if not sparql:
            return Response("Missing parameter query", 400)
        content_type = _handle_header(request.headers.get("accept"))
        results = graph.query(sparql, processor=processor)
        response = results.serialize(format=CONTENT_TYPE_TO_RDFLIB_FORMAT[content_type])
        return Response(response, content_type=content_type)

    return blueprint


def get_fastapi_router(
    converter: Converter, route: str = "/sparql", **kwargs: Any
) -> "fastapi.APIRouter":
    """Get a router for :class:`fastapi.FastAPI`.

    :param converter: A converter
    :param route: The route of the SPARQL service (relative to the base of the API router)
    :param kwargs: Keyword arguments passed through to :class:`fastapi.APIRouter`
    :return: A router
    """
    from fastapi import APIRouter, Query, Request, Response
    from pydantic import BaseModel

    class QueryModel(BaseModel):  # type:ignore
        """A model representing the body in POST queries."""

        query: str

    api_router = APIRouter(**kwargs)
    graph = MappingServiceGraph(converter=converter)
    processor = MappingServiceSPARQLProcessor(graph=graph)

    def _resolve(request: Request, sparql: str) -> Response:
        content_type = _handle_header(request.headers.get("accept"))
        results = graph.query(sparql, processor=processor)
        response = results.serialize(format=CONTENT_TYPE_TO_RDFLIB_FORMAT[content_type])
        return Response(response, media_type=content_type)

    @api_router.get(route)  # type:ignore
    def resolve_get(
        request: Request,
        query: str = Query(title="Query", description="The SPARQL query to run"),  # noqa:B008
    ) -> Response:
        """Run a SPARQL query and serve the results."""
        return _resolve(request, query)

    @api_router.post(route)  # type:ignore
    def resolve_post(request: Request, query: QueryModel) -> Response:
        """Run a SPARQL query and serve the results."""
        return _resolve(request, query.query)

    return api_router


def get_flask_mapping_app(converter: Converter) -> "flask.Flask":
    """Get a Flask app for the mapping service."""
    from flask import Flask

    blueprint = get_flask_mapping_blueprint(converter)
    app = Flask(__name__)
    app.register_blueprint(blueprint)
    return app


def get_fastapi_mapping_app(converter: Converter) -> "fastapi.FastAPI":
    """Get a FastAPI app.

    :param converter: A converter
    :return: A FastAPI app
    """
    from fastapi import FastAPI

    router = get_fastapi_router(converter)
    app = FastAPI()
    app.include_router(router)
    return app
