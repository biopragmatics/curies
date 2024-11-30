"""Typing utilities."""

from __future__ import annotations

from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from typing_extensions import Self

from .api import Converter

__all__ = [
    "CURIE",
    "URI",
    "Prefix",
]

#: From https://stackoverflow.com/a/55038380
NCNAME_RE = r"^[a-zA-Z_][\w.-]*$"


def _get_converter_from_context(info: core_schema.ValidationInfo) -> Converter | None:
    context = info.context or {}
    if isinstance(context, Converter):
        return context
    elif isinstance(context, dict):
        return context.get("converter")
    else:
        raise TypeError


class Prefix(str):
    """A string that is validated as a CURIE prefix.

    This class is a subclass of Python's built-in string class,
    so you can wrap any string with it:

    .. code-block:: python

        from curies import Prefix

        prefix = Prefix("CHEBI")

    You can implicitly type annotate data with this class:

    .. code-block:: python

        from curies import Prefix

        prefix_map: dict[Prefix, str] = {
            "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        }

    When used inside a Pydantic model, this class knows how to
    do validation that the prefix matches the regular expression
    for an XSD NCName. Here's an example usage with Pydantic:

    .. code-block:: python

        from curies import Prefix
        from pydantic import BaseModel

        class ResourceInfo(BaseModel):
            prefix: Prefix
            name: str

        model = ResourceInfo.model_validate({
            "prefix": "CHEBI",
            "name": "Chemical Entities of Biological Interest",
        })

        # raises a pydantic.ValidationError, because the prefix
        # doesn't match the NCName pattern
        ResourceInfo.model_validate({
            "prefix": "$nope",
            "name": "An invalid semantic space!",
        })

    This class implements a hook that uses Pydantic's "context"
    for validation that lets you pass a :class:`Converter` to check
    for existence and standardization with respect to the context
    in the converter:

    .. code-block:: python

        from curies import Prefix, get_obo_converter
        from pydantic import BaseModel

        class ResourceInfo(BaseModel):
            prefix: Prefix
            name: str

        converter = get_obo_converter()
        model = ResourceInfo.model_validate(
            {
                "prefix": "CHEBI",
                "name": "Chemical Entities of Biological Interest",
            },
            context=converter,
        )

        # The following fails because the prefix is not registered
        # in the OBO Foundry, and is therefore not part of the
        # OBO converter
        ResourceInfo.model_validate(
            {
                "prefix": "efo",
                "name": "Experimental Factor Ontology",
            },
            context=converter,
        )
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.AfterValidatorFunctionSchema:
        return core_schema.with_info_after_validator_function(
            cls._validate,
            # TODO check what strict means
            core_schema.str_schema(pattern=NCNAME_RE, strict=False),
        )

    @classmethod
    def _validate(cls, __input_value: str, info: core_schema.ValidationInfo) -> Self:
        converter = _get_converter_from_context(info)
        if converter is None:
            return cls(__input_value)
        return cls(converter.standardize_prefix(__input_value, strict=True))


class CURIE(str):
    """A string that is validated as a CURIE.

    If an optional converter is passed as context during validation,
    then additionally checks if it's standardized with respect to the
    converter.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.AfterValidatorFunctionSchema:
        return core_schema.with_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(strict=False),
        )

    @classmethod
    def _validate(cls, __input_value: str, info: core_schema.ValidationInfo) -> Self:
        converter = _get_converter_from_context(info)
        if converter is None:
            return cls(__input_value)
        return cls(converter.standardize_curie(__input_value, strict=True))


class URI(str):
    """A string that is validated as a URI.

    If an optional converter is passed as context during validation,
    then additionally checks if it's standardized with respect to the
    converter.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.AfterValidatorFunctionSchema:
        return core_schema.with_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(strict=False),
        )

    @classmethod
    def _validate(cls, __input_value: str, info: core_schema.ValidationInfo) -> Self:
        converter = _get_converter_from_context(info)
        if converter is None:
            return cls(__input_value)
        return cls(converter.standardize_uri(__input_value, strict=True))
