"""Mixin classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Generic, Literal, TypeVar, overload

from typing_extensions import Self

from .api import Converter

__all__ = [
    "SemanticallyProcessable",
    "SemanticallyStandardizable",
    "process",
    "process_many",
    "standardize",
    "standardize_many",
]

X = TypeVar("X")


class SemanticallyProcessable(ABC, Generic[X]):
    """A class that can be processed with a converter.

    The goal of this class is to standardize objects that come with unprocessed URIs
    that can be processed into references with respect to a :class:`curies.Converter`.
    For example, this is useful for :mod:`obographs` and :mod:`jskos`.

    .. code-block:: python

        from pydantic import BaseModel
        from curies import SemanticallyProcessable


        class ProcessedEntity(BaseModel):
            reference: Reference


        class RawEntity(BaseModel, SemanticallyProcessable[ProcessedEntity]):
            uri: str

            def process(self, converter: Converter) -> ProcessedEntity:
                return ProcessedEntity(
                    reference=converter.parse_uri(self.uri, strict=True).to_pydantic()
                )

    :mod:`curies` provides a high-level interface for standardizing classes in
    :func:`curies.process`.

    .. code-block:: python

        from curies import Converter

        converter = Converter.from_prefix_map({"CHEBI": "http://purl.obolibrary.org/obo/CHEBI_"})

        e1 = RawEntity(uri="http://purl.obolibrary.org/obo/CHEBI_1")
        e2 = RawEntity(uri="http://purl.obolibrary.org/obo/CHEBI_2")

        # can be used directly on an object
        assert ProcessedEntity(reference=Reference.from_curie("CHEBI:1")) == curies.standardize(
            e1, converter
        )

        # can also be used on an iterable/collection
        assert [
            ProcessedEntity(reference=Reference.from_curie("CHEBI:1")),
            ProcessedEntity(reference=Reference.from_curie("CHEBI:2")),
        ] == curies.process((e1, e2), converter)
    """

    @abstractmethod
    def process(self, converter: Converter) -> X:
        """Process this raw instance."""
        raise NotImplementedError


# docstr-coverage:excused `overload`
@overload
def process(instances: None, converter: Converter, *, iterable: bool = ...) -> None: ...


# docstr-coverage:excused `overload`
@overload
def process(
    instances: SemanticallyProcessable[X], converter: Converter, *, iterable: bool = ...
) -> X: ...


# docstr-coverage:excused `overload`
@overload
def process(
    instances: Iterable[SemanticallyProcessable[X]],
    converter: Converter,
    iterable: Literal[False] = ...,
) -> list[X]: ...


# docstr-coverage:excused `overload`
@overload
def process(
    instances: Iterable[SemanticallyProcessable[X]],
    converter: Converter,
    iterable: Literal[True] = ...,
) -> Iterable[X]: ...


def process(
    instances: SemanticallyProcessable[X] | Iterable[SemanticallyProcessable[X]] | None,
    converter: Converter,
    *,
    return_iterator: bool = False,
) -> X | list[X] | Iterable[X] | None:
    """Process multiple semantically processable instances."""
    if instances is None:
        return None
    elif isinstance(instances, Iterable | list):
        if return_iterator:
            return (instance.process(converter) for instance in instances)
        else:
            return [instance.process(converter) for instance in instances]
    else:
        return instances.process(converter)


process_many = process


class SemanticallyStandardizable(ABC):
    """An object that can be standardized.

    In the following example, a simple object is constructed:

    .. code-block:: python

        from typing_extensions import Self
        from curies import Converter, Reference, SemanticallyStandardizable


        class ReferenceHolder(SemanticallyStandardizable):
            def __init__(self, reference):
                self.reference = reference

            def standardize(self, converter: Converter) -> Self:
                return ReferenceHolder(converter.standardize_reference(self.reference, strict=True))

    It's good form to make these operations return new objects, but there's no reason
    you couldn't update the object in place like in :

    .. code-block:: python

        from typing_extensions import Self
        from curies import Converter, Reference, SemanticallyStandardizable


        class ReferenceHolder(SemanticallyStandardizable):
            def __init__(self, reference):
                self.reference = reference

            def standardize(self, converter: Converter) -> Self:
                self.reference = converter.standardize_reference(self.reference, strict=True)
                return self

    In the following example, the :meth:`pydantic.BaseModel.model_copy` is used to
    automatically reuse all other fields that aren't updated, which creates a new
    object.

    .. code-block:: python

        import datetime
        from typing_extensions import Self
        from curies import Converter, Reference, SemanticallyStandardizable
        from pydantic import BaseModel


        class Triple(BaseModel, SemanticallyStandardizable):
            subject: Reference
            predicate: Reference
            object: Reference
            date_asserted: datetime.date

            def standardize(self, converter: Converter) -> Self:
                return self.model_copy(
                    update={
                        "subject": converter.standardize_reference(self.subject, strict=True),
                        "predicate": converter.standardize_reference(self.predicate, strict=True),
                        "object": converter.standardize_reference(self.object, strict=True),
                    }
                )

    :mod:`curies` provides a high-level interface for standardizing classes in
    :func:`curies.standardize`.

    .. code-block:: python

        from curies import Converter

        converter = Converter()
        converter.add_prefix("CHEBI", "http://purl.obolibrary.org/obo/CHEBI_")
        converter.add_synonym("CHEBI", "chebi")

        r1 = ReferenceHolder(Reference.from_curie("chebi:1"))
        r2 = ReferenceHolder(Reference.from_curie("chebi:2"))

        # can be used directly on an object
        assert ReferenceHolder(Reference.from_curie("CHEBI:1")) == curies.standardize(r1, converter)

        # can also be used on an iterable/collection
        assert [
            ReferenceHolder(Reference.from_curie("CHEBI:1")),
            ReferenceHolder(Reference.from_curie("CHEBI:2")),
        ] == curies.standardize((r1, r2), converter)
    """

    @abstractmethod
    def standardize(self, converter: Converter) -> Self:
        """Standardize all references in the object."""
        raise NotImplementedError


SemanticallyStandardizableType = TypeVar(
    "SemanticallyStandardizableType", bound=SemanticallyStandardizable
)


# docstr-coverage:excused `overload`
@overload
def standardize(instances: None, converter: Converter, *, return_iterator: bool = ...) -> None: ...


# docstr-coverage:excused `overload`
@overload
def standardize(
    instances: SemanticallyStandardizableType, converter: Converter, *, return_iterator: bool = ...
) -> SemanticallyStandardizableType: ...


# docstr-coverage:excused `overload`
@overload
def standardize(
    instances: Iterable[SemanticallyStandardizableType],
    converter: Converter,
    *,
    return_iterator: Literal[True] = ...,
) -> Iterable[SemanticallyStandardizableType]: ...


# docstr-coverage:excused `overload`
@overload
def standardize(
    instances: Iterable[SemanticallyStandardizableType],
    converter: Converter,
    *,
    return_iterator: Literal[False] = ...,
) -> list[SemanticallyStandardizableType]: ...


def standardize(
    instances: SemanticallyStandardizableType | Iterable[SemanticallyStandardizableType] | None,
    converter: Converter,
    *,
    return_iterator: bool = False,
) -> (
    SemanticallyStandardizableType
    | Iterable[SemanticallyStandardizableType]
    | list[SemanticallyStandardizableType]
    | None
):
    """Standardize an instance."""
    if instances is None:
        return None
    elif isinstance(instances, Iterable | list):
        if return_iterator:
            return (instance.standardize(converter) for instance in instances)
        else:
            return [instance.standardize(converter) for instance in instances]
    else:
        return instances.standardize(converter)


standardize_many = standardize
