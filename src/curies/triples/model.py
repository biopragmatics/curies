"""Model definitions."""

from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple, TypeAlias, TypeVar

from pydantic import BaseModel, ConfigDict
from typing_extensions import Self

from ..api import Converter, Reference

__all__ = [
    "StrTriple",
    "Triple",
    "TriplePredicate",
]


class StrTriple(NamedTuple):
    """A triple of curies."""

    subject: str
    predicate: str
    object: str


class Triple(BaseModel):
    """A Pydantic model for a subject-predicate-object triple.

    Triples can be constructed either from strings representing CURIEs or pre-parsed
    :class:`Reference` objects representing CURIEs.

    .. code-block:: python

        from curies import Triple, Reference

        # construction with string representations of CURIEs
        triple = Triple(
            subject="mesh:C000089",
            predicate="skos:exactMatch",
            object="CHEBI:28646",
        )

        # construction with object representations of CURIEs
        triple = Triple(
            subject=Reference(prefix="mesh", identifier="C000089"),
            predicate=Reference(prefix="skos", identifier="exactMatch"),
            object=Reference(prefix="CHEBI", identifier="28646"),
        )

    .. note::

        It's up to you to validate your CURIEs are semantically sound, e.g., against the
        :mod:`bioregistry`.
    """

    model_config = ConfigDict(frozen=True)

    subject: Reference
    predicate: Reference
    object: Reference

    def as_str_triple(self) -> StrTriple:
        """Get a three-tuple of strings representing this triple."""
        return StrTriple(self.subject.curie, self.predicate.curie, self.object.curie)

    def as_uri_triple(self, converter: Converter) -> tuple[str, str, str]:
        """Get a three-tuple of strings representing the expanded URIs."""
        return (
            converter.expand_reference(self.subject, strict=True),
            converter.expand_reference(self.predicate, strict=True),
            converter.expand_reference(self.object, strict=True),
        )

    def __lt__(self, other: Triple) -> bool:
        return self.as_str_triple() < other.as_str_triple()

    @classmethod
    def from_curies(
        cls,
        subject_curie: str,
        predicate_curie: str,
        object_curie: str,
        *,
        reference_cls: type[Reference] = Reference,
    ) -> Self:
        """Construct a triple from three CURIE strings."""
        return cls(
            subject=reference_cls.from_curie(subject_curie),
            predicate=reference_cls.from_curie(predicate_curie),
            object=reference_cls.from_curie(object_curie),
        )

    @classmethod
    def from_uris(
        cls,
        subject: str,
        predicate: str,
        object: str,
        *,
        converter: Converter,
        reference_cls: type[Reference] = Reference,
    ) -> Self:
        """Construct a triple from three URI strings."""
        return cls(
            subject=reference_cls.from_reference(converter.parse_uri(subject, strict=True)),
            predicate=reference_cls.from_reference(converter.parse_uri(predicate, strict=True)),
            object=reference_cls.from_reference(converter.parse_uri(object, strict=True)),
        )


TripleType = TypeVar("TripleType", bound=Triple)

#: A predicate over a triple
TriplePredicate: TypeAlias = Callable[[TripleType], bool]
