from typing import Any, Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from .api import Converter

__all__ = [
    "CURIE",
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
    """A string that is validated as a prefix.

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
            # TODO check what strict means
            core_schema.str_schema(pattern=NCNAME_RE, strict=False),
        )

    @classmethod
    def _validate(cls, __input_value: str, info: core_schema.ValidationInfo) -> Self:
        converter: _get_converter_from_context(info)
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
