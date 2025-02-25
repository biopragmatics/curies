"""Utilities for triples."""

from __future__ import annotations

import csv
import gzip
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from pathlib import Path
from typing import NamedTuple, TextIO

from typing_extensions import Self

from curies import Reference

__all__ = [
    "Triple",
    "read_triples",
    "write_triples",
]


class Triple(NamedTuple):
    """A three-tuple of reference, useful for semantic web applications."""

    subject: Reference
    predicate: Reference
    object: Reference

    @classmethod
    def from_curies(cls, subject_curie: str, predicate_curie: str, object_curie: str) -> Self:
        """Construct a triple from three CURIE strings."""
        return cls(
            Reference.from_curie(subject_curie),
            Reference.from_curie(predicate_curie),
            Reference.from_curie(object_curie),
        )


HEADER = Triple._fields


@contextmanager
def _get_file(path: str | Path, read: bool) -> Generator[TextIO, None, None]:
    path = Path(path).expanduser().resolve()
    if path.suffix == ".gz":
        yield gzip.open(path, mode="rt" if read else "wt")
    else:
        yield open(path, mode="r" if read else "w")


def write_triples(triples: Iterable[Triple], path: str | Path) -> None:
    """Write triples to a file."""
    with _get_file(path, read=False) as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow(HEADER)
        writer.writerows(
            (triple.subject.curie, triple.predicate.curie, triple.object.curie)
            for triple in triples
        )


def read_triples(path: str | Path, *, reference_cls: type[Reference] | None = None) -> list[Triple]:
    """Read triples."""
    if reference_cls is None:
        reference_cls = Reference
    with _get_file(path, read=True) as file:
        reader = csv.reader(file, delimiter="\t")
        _header = next(reader)
        return [
            Triple(
                reference_cls.from_curie(subject_curie),
                reference_cls.from_curie(predicate_curie),
                reference_cls.from_curie(object_curie),
            )
            for subject_curie, predicate_curie, object_curie in reader
        ]
