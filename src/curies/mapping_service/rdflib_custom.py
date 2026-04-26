"""A custom SPARQL processor that optimizes the query based on https://github.com/RDFLib/rdflib/pull/2257."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.evaluate import evalQuery
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue
from rdflib.plugins.sparql.processor import SPARQLProcessor
from rdflib.plugins.sparql.sparql import Query
from rdflib.term import Identifier

__all__ = ["MappingServiceSPARQLProcessor"]


class MappingServiceSPARQLProcessor(SPARQLProcessor):
    """A custom SPARQL processor that optimizes the query based on https://github.com/RDFLib/rdflib/pull/2257.

    Why is this necessary? Ideally, we get queries like

    .. code-block:: sparql

        SELECT * WHERE {
            VALUES ?s { :a :b ... }
            ?s owl:sameAs ?o
        }

    This is fine, since the way that RDFLib parses and constructs an abstract syntax
    tree, the values for ``?s`` get bound properly when calling a custom
    :func:`rdflib.Graph.triples`. However, it's also valid SPARQL to have the ``VALUES``
    clause outside of the ``WHERE`` clause like

    .. code-block:: sparql

        SELECT * WHERE {
            ?s owl:sameAs ?o
        }
        VALUES ?s { :a :b ... }

    Unfortunately, this trips up RDFLib since it doesn't know to bind the values before
    calling ``triples()``, therefore thwarting our custom implementation that
    dynamically generates triples based on the bound values themselves.

    This processor, originally by Jerven Bolleman in
    https://github.com/RDFLib/rdflib/pull/2257, adds some additional logic between
    parsing + constructing the abstract syntax tree and evaluation of the syntax tree.
    Basically, the abstract syntax tree has nodes with two or more children. Jerven's
    clever code (see :func:`_optimize_node` below) finds *Join* nodes that have a
    ``VALUES`` clause in the second of its two arguments, then flips them around. It
    does this recursively for the whole tree. This gets us to the goal of having the
    ``VALUES`` clauses appear first, therefore making sure that their bound values are
    available to the ``triples`` function.
    """

    def query(  # type:ignore[override]
        self,
        strOrQuery: str | Query,  # noqa:N803
        initBindings: Mapping[str, Identifier] | None = None,  # noqa:N803
        initNs: Mapping[str, Any] | None = None,  # noqa:N803
        base: str | None = None,
        DEBUG: bool = False,  # noqa:N803
    ) -> Mapping[Any, Any]:
        """Evaluate a SPARQL query on this processor's graph."""
        if isinstance(strOrQuery, str):
            parse_tree = parseQuery(strOrQuery)
            str_or_qury = translateQuery(parse_tree, base, initNs)
            return self.query(str_or_qury, initBindings=initBindings, base=base)

        strOrQuery.algebra = _optimize_node(strOrQuery.algebra)
        return evalQuery(self.graph, strOrQuery, initBindings or {}, base)


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
