from typing import Any, Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from .api import Converter

#: From https://stackoverflow.com/a/55038380
NCNAME_RE = r"^[a-zA-Z_][\w.-]*$"


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
            core_schema.str_schema(
                pattern=NCNAME_RE,
                strict=False,
            ),
        )

    @classmethod
    def _validate(cls, __input_value: str, info: core_schema.ValidationInfo) -> Self:
        context = info.context or {}
        converter: Converter | None
        if isinstance(context, Converter):
            converter = context
        elif isinstance(context, dict):
            converter = context.get("converter")
        else:
            raise TypeError
        if converter is None:
            return cls(__input_value)
        return cls(converter.standardize_prefix(__input_value, strict=True))
