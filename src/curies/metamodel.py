"""Quick metadata model."""

import csv
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

    # Look into the model to get the type for each field
    # that appears in the names dictionary
    types: dict[str, type[NamableReference]] = {
        curie_key: field_info.annotation
        for curie_key, field_info in cls.model_fields.items()
        if field_info and field_info.annotation and curie_key in names
    }

    for record in records:
        if names:
            for curie_key, name_key in names.items():
                record[curie_key] = types[curie_key].from_curie(
                    record[curie_key], name=record.pop(name_key, None)
                )
        model = cls.model_validate(record)
        yield model
