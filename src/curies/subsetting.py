"""A query language for constructing subsets.

Retrieve all diseases from the `Unified Medical Language System (UMLS)
<https://semantic.farm/umls>`_ by combining several branches identified by their `UMLS
Semantic Types Ontology (STY) <https://semantic.farm/sty>`_ identifiers:

.. code-block:: python

    from curies.subsetting import Union, Descendants, Subsetter

    expression = Union.from_args(
        Descendants(reference="sty:T049", source="umls"),  # cell or molecular dysfunction
        Descendants(reference="sty:T047", source="umls"),  # disease or syndrome
        Descendants(reference="sty:T191", source="umls"),  # neoplastic process
        Descendants(reference="sty:T050", source="umls"),  # experimental model of disease
        Descendants(reference="sty:T048", source="umls"),  # mental or behavioral dysfunction
    )

    # The curies package doesn't implement a concrete evaluation
    # protocol for expressions, but gives an abstract class, e.g.,
    # that PyOBO implements
    subsetter: Subsetter = ...
    references: set[Reference] = subsetter.query(expression)

Retrieve all anatomical terms from the ``A`` branch in the `Medical Subject Headings
(MeSH) <https://semantic.farm/mesh>`_, while skipping the ``A11`` branch, which
corresponds to cell types:

.. code-block:: python

    from curies.subsetting import Descendants, Subsetter

    expression = Descendants(reference="obo:mesh#A", source="mesh") - Descendants(
        reference="obo:mesh#A11", source="mesh"
    )

    # The curies package doesn't implement a concrete evaluation
    # protocol for expressions, but gives an abstract class, e.g.,
    # that PyOBO implements
    subsetter: Subsetter = ...
    references: set[Reference] = subsetter.query(expression)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Annotated, Generic, Literal, Self

from pydantic import BaseModel, Field

from .api import Prefix, Reference, ReferenceType

if TYPE_CHECKING:
    import networkx

__all__ = [
    "Descendants",
    "Difference",
    "Expression",
    "GraphSubsetter",
    "Intersection",
    "Subsetter",
    "Union",
]


class Expression(BaseModel):
    """An expression for subsetting."""

    type: Literal["descendants", "intersection", "union", "difference"]

    def __and__(self, other: Expression) -> Intersection:
        """Take the intersection of this expression with another."""
        match other:
            case Descendants() | Union() | Difference():
                return Intersection(args=[self, other])
            case Intersection():
                return Intersection(args=[self, *other.args])
            case _:
                raise TypeError

    def __or__(self, other: Expression) -> Union:
        """Take the union of this expression with another."""
        match other:
            case Descendants() | Intersection() | Difference():
                return Union(args=[self, other])
            case Union():
                return Union(args=[self, *other.args])
            case _:
                raise TypeError

    def __sub__(self, other: Expression) -> Difference:
        """Take the difference between this expression with another."""
        match other:
            case Descendants() | Union() | Intersection():
                return Difference(left=self, right=other)
            case Difference():
                raise NotImplementedError
            case _:
                raise TypeError


class Descendants(Expression):
    """An expression for the descendants from a given entity."""

    type: Literal["descendants"] = "descendants"
    reference: Reference
    inclusive: bool = False
    source: Annotated[
        Prefix | None,
        Field(
            default=None,
            description="An optional source. If not given, assume the prefix from the reference",
        ),
    ] = None

    def get_source(self) -> Prefix:
        """Get the effective source."""
        return self.source or self.reference.prefix


class Intersection(Expression):
    """The intersection of two or more expressions."""

    type: Literal["intersection"] = "intersection"
    args: Annotated[list[Annotated[Expression, Field(discriminator="type")]], Field(min_length=2)]

    @classmethod
    def from_args(cls, *args: Expression) -> Self:
        """Construct from a sequence."""
        return cls(args=list(args))


class Union(Expression):
    """The union of two or more expressions."""

    type: Literal["union"] = "union"
    args: Annotated[list[Annotated[Expression, Field(discriminator="type")]], Field(min_length=2)]

    @classmethod
    def from_args(cls, *args: Expression) -> Self:
        """Construct from a sequence."""
        return cls(args=list(args))


class Difference(Expression):
    """The difference of two expressions."""

    type: Literal["difference"] = "difference"
    left: Annotated[Expression, Field(discriminator="type")]
    right: Annotated[Expression, Field(discriminator="type")]


class Subsetter(ABC, Generic[ReferenceType]):
    """An implementation for hydrating an expression."""

    @abstractmethod
    def get_descendants(self, descendants: Descendants) -> set[ReferenceType]:
        """Get descendants."""

    def query(self, expr: Expression) -> set[ReferenceType]:
        """Get subset."""
        match expr:
            case Descendants():
                return self.get_descendants(expr)
            case Union():
                union_rv = self.query(expr.args[0])
                for arg in expr.args[1:]:
                    union_rv.update(self.query(arg))
                return union_rv
            case Intersection():
                intersection_rv = self.query(expr.args[0])
                for arg in expr.args[1:]:
                    intersection_rv.intersection_update(self.query(arg))
                return intersection_rv
            case Difference():
                return self.query(expr.left) - self.query(expr.right)
            case _:
                raise TypeError


class GraphSubsetter(Subsetter[ReferenceType], Generic[ReferenceType]):
    """An implementation for hydrating an expression."""

    """A directed graph-based subset evaluator."""

    def __init__(self, graphs: dict[Prefix, networkx.DiGraph[ReferenceType]]) -> None:
        """Initialize the evaluator with directed graphs.

        :param graphs: A mapping from prefixes to directed graphs with the hierarchies
            for the corresponding resources
        """
        self.graphs = graphs

    def get_descendants(self, descendants: Descendants) -> set[ReferenceType]:
        """Get descendants via a directed graph."""
        import networkx as nx

        graph = self.graphs.get(descendants.get_source())
        if graph is None:
            return set()
        rv = set(nx.ancestors(graph, descendants.reference))
        if descendants.inclusive:
            rv.add(descendants.reference)
        return rv
