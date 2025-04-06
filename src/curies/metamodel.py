"""Quick metadata model."""

import csv
import unittest
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from curies import NamableReference

__all__ = [
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
    """
    with open(path) as file:
        reader = csv.DictReader(file, delimiter="\t")
        yield from _from_records(reader, cls, names=names)


def _from_records(
    records: Iterable[dict[str, Any]], cls: type[Model], names: dict[str, str] | None = None
) -> Iterable[Model]:
    for record in records:
        model = cls.model_validate(record)
        yield model


class TestModel(unittest.TestCase):
    """Test parsing models."""

    def test_model(self) -> None:
        """Test parsing into a namable reference."""

        class MM(BaseModel):
            curie: NamableReference

        names = {"curie": "curie_label"}
        records = [
            {"curie": "GO:0000001", "curie_label": "Test 1"},
            {"curie": "GO:0000002", "curie_label": "Test 2"},
        ]

        models = _from_records(records, MM, names=names)
        self.assertEqual(
            [
                MM(curie=NamableReference(prefix="GO", identifier="0000001", name="Test 1")),
                MM(curie=NamableReference(prefix="GO", identifier="0000002", name="Test 2")),
            ],
            models,
        )
