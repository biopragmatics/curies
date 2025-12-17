"""Mixin classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Generic, TypeVar, overload

from typing_extensions import Self

from .api import Converter

__all__ = [
    "SemanticallyProcessable",
    "SemanticallyStandardizable",
    "process_many",
    "standardize_many",
]

X = TypeVar("X")


class SemanticallyProcessable(ABC, Generic[X]):
    """A class that can be processed with a converter.

    The goal of this class is to standardize objects that come with
    unprocessed URIs that can be processed into references with
    respect to a :class:`curies.Converter`. For example, this is
    useful for :mod:`obographs` and :mod:`jskos`.

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
    """

    @abstractmethod
    def process(self, converter: Converter) -> X:
        """Process this raw instance."""
        raise NotImplementedError


# docstr-coverage:excused `overload`
@overload
def process_many(instances: None, converter: Converter) -> None: ...


# docstr-coverage:excused `overload`
@overload
def process_many(
    instances: Iterable[SemanticallyProcessable[X]], converter: Converter
) -> list[X]: ...


def process_many(
    instances: Iterable[SemanticallyProcessable[X]] | None, converter: Converter
) -> list[X] | None:
    """Process multiple semantically processable instances."""
    if instances is None:
        return None
    return [instance.process(converter) for instance in instances]


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

    In the following example, the :meth:`pydantic.BaseModel.model_copy` is
    used to automatically reuse all other fields that aren't updated, which
    creates a new object.

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
    """

    @abstractmethod
    def standardize(self, converter: Converter) -> Self:
        """Standardize all references in the object."""
        raise NotImplementedError


Y = TypeVar("Y", bound=SemanticallyStandardizable)


# docstr-coverage:excused `overload`
@overload
def standardize_many(instances: None, converter: Converter) -> None: ...


# docstr-coverage:excused `overload`
@overload
def standardize_many(instances: Iterable[Y], converter: Converter) -> list[Y]: ...


def standardize_many(instances: Iterable[Y] | None, converter: Converter) -> list[Y] | None:
    """Standardize multiple semantically standardizable instances."""
    if instances is None:
        return None
    return [instance.standardize(converter) for instance in instances]
