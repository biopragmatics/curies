"""I/O operations for triples."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import TextIO

from pystow.utils import safe_open_reader, safe_open_writer

from .model import Triple
from ..api import Reference

__all__ = [
    "HEADER",
    "read_triples",
    "write_triples",
]

#: the default header for a three-column file representing triples
HEADER = list(Triple.model_fields)


def write_triples(
    triples: Iterable[Triple], path: str | Path | TextIO, *, header: Sequence[str] | None = None
) -> None:
    """Write triples as a three-column TSV file."""
    if header is None:
        header = HEADER
    with safe_open_writer(path) as writer:
        writer.writerow(header)
        writer.writerows(
            (triple.subject.curie, triple.predicate.curie, triple.object.curie)
            for triple in triples
        )


def read_triples(
    path: str | Path | TextIO, *, reference_cls: type[Reference] | None = None
) -> list[Triple]:
    """Read triples from a three-column TSV file."""
    if reference_cls is None:
        reference_cls = Reference
    with safe_open_reader(path) as reader:
        _header = next(reader)
        return [
            Triple(
                subject=reference_cls.from_curie(subject_curie),
                predicate=reference_cls.from_curie(predicate_curie),
                object=reference_cls.from_curie(object_curie),
            )
            for subject_curie, predicate_curie, object_curie in reader
        ]
