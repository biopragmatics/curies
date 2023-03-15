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
        query: Union[str, Query],
        initBindings=None,  # noqa:N803
        initNs=None,  # noqa:N803
        base=None,
        DEBUG=False,
    ):
        """Evaluate a SPARQL query on this processor's graph."""
        if isinstance(query, str):
            parse_tree = parseQuery(query)
            query = translateQuery(parse_tree, base, initNs)
        query.algebra = _optimize_node(query.algebra)
        return evalQuery(self.graph, query, initBindings or {}, base)


# From Jerven's PR to RDFLib (https://github.com/RDFLib/rdflib/pull/2257)
def _optimize_node(comp_value: CompValue) -> CompValue:
    if (
        comp_value.name == "Join"
        and comp_value.p1.name != "ToMultiSet"
        and comp_value.p2.name == "ToMultiSet"
    ):
        comp_value.update(p1=comp_value.p2, p2=comp_value.p1)
    for inner_comp_value in comp_value.values():
        if isinstance(inner_comp_value, CompValue):
            _optimize_node(inner_comp_value)
    return comp_value
