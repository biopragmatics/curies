"""Implementation of mapping service."""

import itertools as itt
from typing import TYPE_CHECKING, Any, Collection, Iterable, List, Set, Tuple, Union, cast

from rdflib import OWL, Graph, URIRef
from rdflib.term import _is_valid_uri

from .rdflib_custom import MappingServiceSPARQLProcessor  # type: ignore
from .utils import CONTENT_TYPE_TO_RDFLIB_FORMAT, handle_header
from ..api import Converter

if TYPE_CHECKING:
    import fastapi
    import flask


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
            graph = MappingServiceGraph(converter=converter)

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
        sparql = request.values.get("query")
        if not sparql:
            return Response(
                "Missing query (either in args for GET requests, or in form for POST requests)", 400
            )
        content_type = handle_header(request.headers.get("accept"))
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
    from fastapi import APIRouter, Form, Header, Query, Response

    api_router = APIRouter(**kwargs)
    graph = MappingServiceGraph(converter=converter)
    processor = MappingServiceSPARQLProcessor(graph=graph)

    def _resolve(accept: Header, sparql: str) -> Response:
        content_type = handle_header(accept)
        results = graph.query(sparql, processor=processor)
        response = results.serialize(format=CONTENT_TYPE_TO_RDFLIB_FORMAT[content_type])
        return Response(response, media_type=content_type)

    @api_router.get(route)  # type:ignore
    def resolve_get(
        query: str = Query(description="The SPARQL query to run"),  # noqa:B008
        accept: str = Header(),  # noqa:B008
    ) -> Response:
        """Run a SPARQL query and serve the results."""
        return _resolve(accept, query)

    @api_router.post(route)  # type:ignore
    def resolve_post(
        query: str = Form(description="The SPARQL query to run"),  # noqa:B008
        accept: str = Header(),  # noqa:B008
    ) -> Response:
        """Run a SPARQL query and serve the results."""
        return _resolve(accept, query)

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
