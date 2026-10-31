"""A query language for constructing subsets.

Retrieve all diseases from the `Unified Medical Language System (UMLS)
<https://semantic.farm/umls>`_ by combining several branches identified by their `UMLS
Semantic Types Ontology (STY) <https://semantic.farm/sty>`_ identifiers:

.. code-block:: python

    from curies.subsetting import Union, Descendants, SubsetEvaluator

    expression = Union.from_args(
        Descendants(reference="sty:T049"),  # cell or molecular dysfunction
        Descendants(reference="sty:T047"),  # disease or syndrome
        Descendants(reference="sty:T191"),  # neoplastic process
        Descendants(reference="sty:T050"),  # experimental model of disease
        Descendants(reference="sty:T048"),  # mental or behavioral dysfunction
    )

    # The curies package doesn't implement a concrete evaluation
    # protocol for expressions, but gives an abstract class, e.g.,
    # that PyOBO implements
    evaluator: SubsetEvaluator = ...
    references: set[Reference] = evaluator.evaluate(expression)

Retrieve all anatomical terms from the ``A`` branch in the `Medical Subject Headings
(MeSH) <https://semantic.farm/mesh>`_, while skipping the ``A11`` branch, which
corresponds to cell types:

.. code-block:: python

    from curies.subsetting import Descendants

    expression = Descendants(reference="obo:mesh#A") - Descendants(reference="obo:mesh#A11")

    # The curies package doesn't implement a concrete evaluation
    # protocol for expressions, but gives an abstract class, e.g.,
    # that PyOBO implements
    evaluator: Evaluator = ...
    references: set[Reference] = evaluator.evaluate(expression)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field

from curies import Reference

__all__ = [
    "Descendants",
    "Difference",
    "Expression",
    "Intersection",
    "SubsetEvaluator",
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
    inclusive: bool = True


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


class SubsetEvaluator(ABC):
    """An implementation for hydrating an expression."""

    @abstractmethod
    def get_descendants(self, descendants: Descendants) -> set[Reference]:
        """Get descendants."""

    def evaluate(self, expr: Expression) -> set[Reference]:
        """Get subset."""
        match expr:
            case Descendants():
                return self.get_descendants(expr)
            case Union():
                union_rv = self.evaluate(expr.args[0])
                for arg in expr.args[1:]:
                    union_rv.update(self.evaluate(arg))
                return union_rv
            case Intersection():
                intersection_rv = self.evaluate(expr.args[0])
                for arg in expr.args[1:]:
                    intersection_rv.intersection_update(self.evaluate(arg))
                return intersection_rv
            case Difference():
                return self.evaluate(expr.left) - self.evaluate(expr.right)
            case _:
                raise TypeError
