"""Quick metadata model."""

from __future__ import annotations

import csv
import types
import typing
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from curies import NamableReference

__all__ = [
    "from_tsv",
    "iter_records",
]

Model = TypeVar("Model", bound=BaseModel)


def from_tsv(
    path: str | Path, cls: type[Model], names: dict[str, str] | None = None
) -> Iterable[Model]:
    """Load models from a TSV.

    :param path: The path to a TSV file
    :param cls: The model class to parse into
    :param names:
        A mapping from column names corresponding to reference fields to column names representing the labels
    :yields: Validated models

    Let's use a similar table, now with the prefix and identifier combine into CURIEs.

    =========== ======== ======
    curie       name     smiles
    =========== ======== ======
    CHEBI:16236 ethanol  CCO
    CHEBI:28831 propanol CCCO
    CHEBI:44884 pentanol CCCCCO
    =========== ======== ======

    In the following code, we simulate reading that file and show where the error shows up:

    .. code-block:: python

        from pydantic import BaseModel

        from curies import NamedReference
        from curies.metamodel import iter_records


        class Row(BaseModel):
            curie: NamedReference
            smiles: str


        records = [
            {"curie": "CHEBI:16236", "name": "ethanol", "smiles": "CCO"},
            {"curie": "CHEBI:28831", "name": "propanol", "smiles": "CCCO"},
            {"curie": "CHEBI:44884", "name": "pentanol", "smiles": "CCCCCO"},
        ]

        models = list(iter_records(records, Row, names={"curie": "name"}))
        print(models)

    In the following example, we encode SSSOM in a Pydantic model:

    .. code-block:: python

        import datetime
        from typing import Literal

        from pydantic import BaseModel, ConfigDict, Field
        from curies import NamableReference, Reference
        from curies.metamodel import iter_records


        class SemanticMapping(BaseModel):
            # required when using aliases
            model_config = ConfigDict(
                populate_by_name=True,
            )

            subject: NamableReference = Field(..., alias="subject_id")
            predicate: NamableReference = Field(..., alias="predicate_id")
            predicate_modifier: Literal["Not"] | None = Field(None)
            object: NamableReference = Field(..., alias="object_id")
            mapping_justification: Reference = Field(...)
            license: Reference | None = Field(None)
            creator: NamableReference | None = Field(None, alias="creator_id")
            author: NamableReference | None = Field(None, alias="author_id")
            reviewer: NamableReference | None = Field(None, alias="reviewer_id")
            publication_date: datetime.date | None = Field(None)
            issue_tracker_item: str | None = Field(None)
            comment: str | None = Field(None)


        records = [
            {
                "subject_id": "CHEBI:16236",
                "subject_label": "ethanol",
                "predicate_id": "skos:exactMatch",
                "object_id": "pubchem.compound:702",
                "mapping_justification": "semapv:ManualMappingCuration",
            },
            {
                "subject_id": "CHEBI:28831",
                "subject_label": "propanol",
                "predicate_id": "skos:exactMatch",
                "object_id": "pubchem.compound:1031",
                "mapping_justification": "semapv:ManualMappingCuration",
            },
            {
                "subject_id": "CHEBI:44884",
                "subject_label": "pentanol",
                "predicate_id": "skos:exactMatch",
                "object_id": "pubchem.compound:6276",
                "mapping_justification": "semapv:ManualMappingCuration",
            },
        ]

        models = list(
            iter_records(
                records,
                SemanticMapping,
                names={
                    "subject_id": "subject_label",
                    "predicate_id": "predicate_label",
                    "object_id": "object_label",
                    "author_id": "author_label",
                    "reviewer_id": "reviewer_label",
                    "creator_id": "creator_label",
                },
            )
        )
        print(models)

    """
    path = Path(path).expanduser().resolve()
    with path.open() as file:
        reader = csv.DictReader(file, delimiter="\t")
        yield from iter_records(reader, cls, names=names)


def iter_records(
    records: Iterable[dict[str, Any]], cls: type[Model], names: dict[str, str] | None = None
) -> Iterable[Model]:
    """Get records."""
    if names is None:
        names = {}

    # maps from aliases back to the names of the fields in the Pydantic model class
    # e.g., in SSSOM, we map `subject_id` as an alias to `subject` as the field name
    # in the Pydantic model class
    alias_to_field: dict[str, str] = {}
    field_to_alias: dict[str, str] = {}
    for key, model_field in cls.model_fields.items():
        if model_field.alias:
            field_to_alias[key] = model_field.alias
            alias_to_field[model_field.alias] = key

    # Check that all keys in the names dictionary
    # are actually in the model
    for curie_key, name_key in names.items():
        norm_curie_key = alias_to_field.get(curie_key)
        if norm_curie_key is None:
            raise ValueError(
                f"Incorrectly specified name reconciliation key - {curie_key} is not a model field"
            )
        if name_key in alias_to_field:
            raise ValueError(f"name key {name_key} should not appear as a model field nor alias")

    # check that no values are used for multiple columns
    counter = Counter(names.values())
    bad_keys = {key for key, count in counter.items() if count > 1}
    if bad_keys:
        raise ValueError(f"duplicate usage of name columns: {bad_keys}")

    # Look into the model to get the type for each field
    # that appears in the names dictionary
    alias_to_type: dict[str, type[NamableReference]] = {}
    for curie_key, field_info in cls.model_fields.items():
        if not field_info or not field_info.annotation:
            raise ValueError
        norm_curie_key = field_to_alias.get(curie_key, curie_key)
        alias_to_type[norm_curie_key] = _strip_optional(field_info.annotation)

    for record in records:
        if names:
            for curie_key, name_key in names.items():
                if curie_key not in record:
                    continue
                reference_cls: type[NamableReference] = alias_to_type[curie_key]
                record[curie_key] = reference_cls.from_curie(
                    record.pop(curie_key), name=record.pop(name_key, None)
                )

        model = cls.model_validate(record)
        yield model


def _strip_optional(x: Any) -> Any:
    if typing.get_origin(x) != types.UnionType:
        return x
    else:
        args = [arg for arg in typing.get_args(x) if arg is not type(None)]
        if len(args) == 1:
            return args[0]
        else:
            raise NotImplementedError
