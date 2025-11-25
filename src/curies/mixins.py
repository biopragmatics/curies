"""Mixin classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from typing_extensions import Self

from .api import Converter

__all__ = [
    "PrefixGettable",
    "SemanticallyProcessable",
    "SemanticallyStandardizable",
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


class PrefixGettable(ABC):
    """An object that contains references with prefixes.

    .. code-block:: python

        from pydantic import BaseModel
        from curies.mixins import PrefixGettable


        class Triple(BaseModel, PrefixGettable):
            subject: Reference
            predicate: Reference
            object: Reference

            def get_prefixes(self) -> set[str]:
                return {self.subject.prefix, self.predicate.prefix, self.object.prefix}
    """

    @abstractmethod
    def get_prefixes(self) -> set[str]:
        """Get all prefixes used by the object."""
        raise NotImplementedError
