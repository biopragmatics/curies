# -*- coding: utf-8 -*-
# type: ignore

"""A custom SPARQL processor that optimizes the query based on https://github.com/RDFLib/rdflib/pull/2257."""

from typing import Union

from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.evaluate import evalQuery
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue
from rdflib.plugins.sparql.processor import SPARQLProcessor
from rdflib.plugins.sparql.sparql import Query

__all__ = ["JervenSPARQLProcessor"]


class JervenSPARQLProcessor(SPARQLProcessor):
    """A custom SPARQL processor that optimizes the query based on https://github.com/RDFLib/rdflib/pull/2257."""

    def query(self, strOrQuery: Union[str, Query], initBindings=None, initNs=None, base=None, DEBUG=False):
        """Evaluate a SPARQL query on this processor's graph."""
        if not isinstance(strOrQuery, Query):
            parsetree = parseQuery(strOrQuery)
            query = translateQuery(parsetree, base, initNs)
        else:
            query = strOrQuery
        query.algebra = _optimize_node(query.algebra)
        return evalQuery(self.graph, query, initBindings or {}, base)


# From Jerven's PR to RDFLib (https://github.com/RDFLib/rdflib/pull/2257)
def _optimize_node(cv: CompValue) -> CompValue:
    if cv.name == "Join" and cv.p1.name != "ToMultiSet" and cv.p2.name == "ToMultiSet":
        cv.update(p1=cv.p2, p2=cv.p1)
    for k, v in cv.items():
        if isinstance(v, CompValue):
            _optimize_node(v)
    return cv
