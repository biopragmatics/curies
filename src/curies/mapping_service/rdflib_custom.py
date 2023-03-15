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

    def query(
        self,
        strOrQuery: Union[str, Query],  # noqa:N803
        initBindings=None,
        initNs=None,
        base=None,
        DEBUG=False,
    ):
        """Evaluate a SPARQL query on this processor's graph."""
        if not isinstance(strOrQuery, Query):
            parsetree = parseQuery(strOrQuery)
            query = translateQuery(parsetree, base, initNs)
        else:
            query = strOrQuery
        query.algebra = _optimize_node(query.algebra)
        return evalQuery(self.graph, query, initBindings or {}, base)


# From Jerven's PR to RDFLib (https://github.com/RDFLib/rdflib/pull/2257)
def _optimize_node(comp_value: CompValue) -> CompValue:
    if (
        comp_value.name == "Join"
        and comp_value.p1.name != "ToMultiSet"
        and comp_value.p2.name == "ToMultiSet"
    ):
        p1, p2 = comp_value.p2, comp_value.p1
        #  print("left", comp_value.p1)
        #  print("right", comp_value.p2)
        comp_value.update(p1=p1, p2=p2)
    for inner_comp_value in comp_value.values():
        if isinstance(inner_comp_value, CompValue):
            _optimize_node(inner_comp_value)
    return comp_value
