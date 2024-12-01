"""Typing utilities."""

from __future__ import annotations

from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema
from typing_extensions import Self

from .api import _get_converter_from_context

__all__ = [
    "CURIE",
    "URI",
]


class CURIE(str):
    """A string that is validated by Pydantic as a CURIE.

    This class is a subclass of Python's built-in string class,
    so you can wrap any string with it:

    .. code-block:: python

        from curies import CURIE

        curie = CURIE("CHEBI:16236")

    You can implicitly type annotate data with this class:

    .. code-block:: python

        from curies import CURIE

        chemical_to_smiles: dict[CURIE, str] = {
            "CHEBI:16236": "CCO",
            "CHEBI:28831": "CCCO",
        }

    .. seealso::

        We haven't yet established a reliable regular expression
        for validating CURIEs. Therefore, unlike :class:`Prefix`,
        there's no direct validation (yet). Here are a few places
        to look for discussion:

        - https://www.w3.org/2010/02/rdfa/track/issues/138
        - https://gist.github.com/niklasl/2506955
        - https://github.com/biopragmatics/curies/issues/77
        - https://github.com/linkml/linkml-runtime/pull/280


    When used inside a Pydantic model in combination with passing
    a :class:`Converter` to the "context" to the ``model_validate``
    function, it can check for valid CURIEs.

    This class implements a hook that uses Pydantic's "context"
    for validation that lets you pass a :class:`Converter` to check
    for existence and standardization with respect to the context
    in the converter:

    .. code-block:: python

        from curies import CURIE, get_obo_converter
        from pydantic import BaseModel

        class SmilesAnnotation(BaseModel):
            curie: CURIE
            name: str

        converter = get_obo_converter()
        model = SmilesAnnotation.model_validate(
            {
                "curie": "CHEBI:16236",
                "curie": "CCO",
            },
            context=converter,
        )

        # raises a pydantic.ValidationError, because the prefix
        # is not registered in the OBO Foundry, and is therefore
        # not part of the OBO converter
        SmilesAnnotation.model_validate(
            {
                "curie": "efo:12345",
                "smiles": "CCO",
            },
            context=converter,
        )

        # In case you need to pass more arbitrary
        # context, you can also use a dict with the key
        # "converter"
        SmilesAnnotation.model_validate(
            {
                "curie": "CHEBI:16236",
                "curie": "CCO",
            },
            context={
                "converter": converter,
                ...
            },
        )
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
    """A string that is validated by Pydantic as a URI.

    This class is a subclass of Python's built-in string class,
    so you can wrap any string with it:

    .. code-block:: python

        from curies import URI

        uri = URI("http://purl.obolibrary.org/obo/CHEBI_16236")

    You can implicitly type annotate data with this class:

    .. code-block:: python

        from curies import URI

        chemical_to_smiles: dict[URI, str] = {
            "http://purl.obolibrary.org/obo/CHEBI_16236": "CCO",
            "http://purl.obolibrary.org/obo/CHEBI_28831": "CCCO",
        }

    When used inside a Pydantic model in combination with passing
    a :class:`Converter` to the "context" to the ``model_validate``
    function, it can check for valid URIs
    (i.e., ones that can be compressed!).

    .. code-block:: python

        from curies import URI, get_obo_converter
        from pydantic import BaseModel

        class URISmilesAnnotation(BaseModel):
            uri: URI
            name: str

        converter = get_obo_converter()
        model = URISmilesAnnotation.model_validate(
            {
                "uri": "http://purl.obolibrary.org/obo/CHEBI_16236",
                "curie": "CCO",
            },
            context=converter,
        )

        # raises a pydantic.ValidationError, because the prefix
        # is not registered in the OBO Foundry, and is therefore
        # not part of the OBO converter
        URISmilesAnnotation.model_validate(
            {
                "uri": "http://www.ebi.ac.uk/efo/EFO_12345",
                "smiles": "CCO",
            },
            context=converter,
        )

        # In case you need to pass more arbitrary
        # context, you can also use a dict with the key
        # "converter"
        URISmilesAnnotation.model_validate(
            {
                "uri": "http://purl.obolibrary.org/obo/CHEBI_16236",
                "curie": "CCO",
            },
            context={
                "converter": converter,
                ...
            },
        )

    .. warning::

        Many semantic web applications can accept "any" URI in
        some places, even ones that aren't part of a well-defined semantic
        space. If your application works this way, then don't use this field
        for validation!

        One example where this might happen is if you're using old-school
        URLs for annotating licenses. This means you might want to write
        https://creativecommons.org/publicdomain/zero/1.0/ for the
        Creative Commons Zero 1.0 license,
        but this itself isn't part of some semantic space for licenses,
        so it's not an appropriate place to annotate your data model with
        :class:`URI` if license URLs go there.
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
