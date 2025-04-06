"""Quick metadata model."""

import csv
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from curies import NamableReference

__all__ = [
    "from_records",
    "from_tsv",
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

    Note that there's a typo in the prefix on the fourth row in the prefix because it uses
    ``CHOBI`` instead of ``CHEBI``. In the following code, we simulate reading that file and
    show where the error shows up:

    .. code-block:: python

        import csv
        from pydantic import BaseModel, ValidationError
        from curies import Converter, NamedReference
        from curies.metamodel import from_records

        converter = Converter.from_prefix_map(
            {
                "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
            }
        )


        class Row(BaseModel):
            curie: NamedReference
            smiles: str


        records = [
            {"curie": "CHEBI:16236", "name": "ethanol", "smiles": "CCO"},
            {"curie": "CHEBI:28831", "name": "propanol", "smiles": "CCCO"},
            {"curie": "CHOBI:44884", "name": "pentanol", "smiles": "CCCCCO"},
        ]

        models = list(from_records(records, Row, names={"curie": "name"}))
        print(models)

    """
    with open(path) as file:
        reader = csv.DictReader(file, delimiter="\t")
        yield from from_records(reader, cls, names=names)


def from_records(
    records: Iterable[dict[str, Any]], cls: type[Model], names: dict[str, str] | None = None
) -> Iterable[Model]:
    """Get records."""
    for record in records:
        if names:
            for k, v in names.items():
                record[k] = NamableReference.from_curie(record[k], name=record.pop(v, None))
        model = cls.model_validate(record)
        yield model
