"""
Custom re-implementation of RDFLib's algebra, so we can
more efficiently join values clause first. This all has been done
to change the following one line:

.. code-block:: python

    if q.valuesClause:
        M = Join(p2=M, p1=ToMultiSet(translateValues(q.valuesClause)))

to

.. code-block:: python

    if q.valuesClause:
        M = Join(p1=ToMultiSet(translateValues(q.valuesClause)), p2=M)

Code in this module has been copied (mostly verbatim, save some style
changes) from RDFLib (https://github.com/RDFLib/rdflib) under the
BSD-3-Clause license (https://github.com/RDFLib/rdflib/blob/main/LICENSE)

Huge thanks to the RDFLib developers.
"""

import functools
from typing import List, Mapping, Optional, Set, Tuple

from pyparsing import ParseResults
from rdflib.plugins.sparql.algebra import (
    Extend,
    Filter,
    Group,
    Join,
    OrderBy,
    Project,
    ToMultiSet,
    _addVars,
    _findVars,
    _hasAggregate,
    _simplifyFilters,
    _traverse,
    _traverseAgg,
    analyse,
    simplify,
    translateAggregates,
    translateGroupGraphPattern,
    translatePath,
    translatePName,
    translatePrologue,
    translateValues,
    traverse,
    triples,
)
from rdflib.plugins.sparql.evaluate import evalQuery
from rdflib.plugins.sparql.operators import and_
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue
from rdflib.plugins.sparql.processor import SPARQLProcessor
from rdflib.plugins.sparql.sparql import Query
from rdflib.term import Variable

__all__ = ["CustomSPARQLProcessor"]


class CustomSPARQLProcessor(SPARQLProcessor):
    def query(self, query, initBindings=None, initNs=None, base=None, DEBUG=False):
        if not isinstance(query, Query):
            parsetree = parseQuery(query)
            query = translateQuery(parsetree, base, initNs or {})
        return evalQuery(self.graph, query, initBindings or {}, base)


def translateQuery(
    q: ParseResults,
    base: Optional[str] = None,
    initNs: Optional[Mapping[str, str]] = None,
) -> Query:
    """
    Translate a query-parsetree to a SPARQL Algebra Expression

    Return a rdflib.plugins.sparql.sparql.Query object
    """

    # We get in: (prologue, query)

    prologue = translatePrologue(q[0], base, initNs)

    # absolutize/resolve prefixes
    q[1] = traverse(q[1], visitPost=functools.partial(translatePName, prologue=prologue))

    P, PV = translate(q[1])
    datasetClause = q[1].datasetClause
    if q[1].name == "ConstructQuery":
        template = triples(q[1].template) if q[1].template else None

        res = CompValue(q[1].name, p=P, template=template, datasetClause=datasetClause)
    else:
        res = CompValue(q[1].name, p=P, datasetClause=datasetClause, PV=PV)

    res = traverse(res, visitPost=simplify)
    _traverseAgg(res, visitor=analyse)
    _traverseAgg(res, _addVars)

    return Query(prologue, res)


def translate(q: CompValue) -> Tuple[CompValue, List[Variable]]:
    """
    http://www.w3.org/TR/sparql11-query/#convertSolMod
    """
    _traverse(q, _simplifyFilters)

    q.where = traverse(q.where, visitPost=translatePath)

    # TODO: Var scope test
    VS: Set[Variable] = set()
    traverse(q.where, functools.partial(_findVars, res=VS))

    # all query types have a where part
    M = translateGroupGraphPattern(q.where)

    aggregate = False
    if q.groupby:
        conditions = []
        # convert "GROUP BY (?expr as ?var)" to an Extend
        for c in q.groupby.condition:
            if isinstance(c, CompValue) and c.name == "GroupAs":
                M = Extend(M, c.expr, c.var)
                c = c.var
            conditions.append(c)

        M = Group(p=M, expr=conditions)
        aggregate = True
    elif (
        traverse(q.having, _hasAggregate, complete=False)
        or traverse(q.orderby, _hasAggregate, complete=False)
        or any(
            traverse(x.expr, _hasAggregate, complete=False) for x in q.projection or [] if x.evar
        )
    ):
        # if any aggregate is used, implicit group by
        M = Group(p=M)
        aggregate = True

    if aggregate:
        M, E = translateAggregates(q, M)
    else:
        E = []

    # HAVING
    if q.having:
        M = Filter(expr=and_(*q.having.condition), p=M)

    # VALUES
    if q.valuesClause:
        # THIS IS THE LINE WE CHANGED IN :mod:`curies`
        M = Join(p2=M, p1=ToMultiSet(translateValues(q.valuesClause)))

    if not q.projection:
        # select *
        PV = list(VS)
    else:
        PV = list()
        for v in q.projection:
            if v.var:
                if v not in PV:
                    PV.append(v.var)
            elif v.evar:
                if v not in PV:
                    PV.append(v.evar)

                E.append((v.expr, v.evar))
            else:
                raise Exception("I expected a var or evar here!")

    for e, v in E:
        M = Extend(M, e, v)

    # ORDER BY
    if q.orderby:
        M = OrderBy(
            M,
            [CompValue("OrderCondition", expr=c.expr, order=c.order) for c in q.orderby.condition],
        )

    # PROJECT
    M = Project(M, PV)

    if q.modifier:
        if q.modifier == "DISTINCT":
            M = CompValue("Distinct", p=M)
        elif q.modifier == "REDUCED":
            M = CompValue("Reduced", p=M)

    if q.limitoffset:
        offset = 0
        if q.limitoffset.offset is not None:
            offset = q.limitoffset.offset.toPython()

        if q.limitoffset.limit is not None:
            M = CompValue("Slice", p=M, start=offset, length=q.limitoffset.limit.toPython())
        else:
            M = CompValue("Slice", p=M, start=offset)

    return M, PV
