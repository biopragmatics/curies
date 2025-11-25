"""Mixin classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from typing_extensions import Self

from .api import Converter

__all__ = [
    "SemanticallyProcessable",
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


class Standardizable:
    """An object that can be standardized."""

    def standardize(self, converter: Converter) -> Self:
        """Standardize all references in the object."""
        raise NotImplementedError
