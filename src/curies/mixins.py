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
    """

    @abstractmethod
    def process(self, converter: Converter) -> X:
        """Process this raw instance."""
        raise NotImplementedError


Z = TypeVar("Z", bound=SemanticallyProcessable)


# docstr-coverage:excused `overload`
@overload
def process(instances: None, converter: Converter, *, iterable: bool = ...) -> None: ...


# docstr-coverage:excused `overload`
@overload
def process(instances: Z, converter: Converter, *, iterable: bool = ...) -> Z: ...


# docstr-coverage:excused `overload`
@overload
def process(
    instances: Iterable[Z], converter: Converter, iterable: Literal[False] = ...
) -> list[Z]: ...


# docstr-coverage:excused `overload`
@overload
def process(
    instances: Iterable[Z], converter: Converter, iterable: Literal[True] = ...
) -> Iterable[Z]: ...


def process(
    instances: Z | Iterable[Z] | None, converter: Converter, *, iterable: bool = False
) -> Z | list[Z] | Iterable[Z] | None:
    """Process multiple semantically processable instances."""
    if instances is None:
        return None
    elif isinstance(instances, Iterable | list):
        if iterable:
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

        t1 = Triple(subject="a:1", predicate="b:1", object="c:1")
        curies.standardize(t1, converter)
    """

    @abstractmethod
    def standardize(self, converter: Converter) -> Self:
        """Standardize all references in the object."""
        raise NotImplementedError


Y = TypeVar("Y", bound=SemanticallyStandardizable)


# docstr-coverage:excused `overload`
@overload
def standardize(instances: None, converter: Converter, *, iterable: bool = ...) -> None: ...


# docstr-coverage:excused `overload`
@overload
def standardize(instances: Y, converter: Converter, *, iterable: bool = ...) -> Y: ...


# docstr-coverage:excused `overload`
@overload
def standardize(
    instances: Iterable[Y], converter: Converter, *, iterable: Literal[True] = ...
) -> Iterable[Y]: ...


# docstr-coverage:excused `overload`
@overload
def standardize(
    instances: Iterable[Y], converter: Converter, *, iterable: Literal[False] = ...
) -> list[Y]: ...


def standardize(
    instances: Y | Iterable[Y] | None, converter: Converter, *, iterable: bool = False
) -> Y | Iterable[Y] | list[Y] | None:
    """Standardize an instance."""
    if instances is None:
        return None
    elif isinstance(instances, Iterable | list):
        if iterable:
            return (instance.standardize(converter) for instance in instances)
        else:
            return [instance.standardize(converter) for instance in instances]
    else:
        return instances.standardize(converter)


standardize_many = standardize
