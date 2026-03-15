"""Utilities for triples."""

from __future__ import annotations

import base64
import csv
import gzip
from collections.abc import Generator, Iterable, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import NamedTuple, TextIO, cast

from pydantic import BaseModel, ConfigDict
from typing_extensions import Self

from .api import Converter, Reference

__all__ = [
    "StrTriple",
    "Triple",
    "decode_triple",
    "encode_triple",
    "read_triples",
    "write_triples",
]


class StrTriple(NamedTuple):
    """A triple of curies."""

    subject: str
    predicate: str
    object: str


class Triple(BaseModel):
    """A model for a triple of subject-predicate-object triple."""

    model_config = ConfigDict(frozen=True)

    subject: Reference
    predicate: Reference
    object: Reference

    def as_str_triple(self) -> StrTriple:
        """Get a three-tuple of strings representing this triple."""
        return StrTriple(self.subject.curie, self.predicate.curie, self.object.curie)

    def as_uri_triple(self, converter: Converter) -> tuple[str, str, str]:
        """Get a three-tuple of strings representing the expanded URIs."""
        return (
            converter.expand(self.subject, strict=True),
            converter.expand(self.predicate, strict=True),
            converter.expand(self.object, strict=True),
        )

    def __lt__(self, other: Triple) -> bool:
        return self.as_str_triple() < other.as_str_triple()

    @classmethod
    def from_curies(
        cls,
        subject_curie: str,
        predicate_curie: str,
        object_curie: str,
        *,
        reference_cls: type[Reference] = Reference,
    ) -> Self:
        """Construct a triple from three CURIE strings."""
        return cls(
            subject=reference_cls.from_curie(subject_curie),
            predicate=reference_cls.from_curie(predicate_curie),
            object=reference_cls.from_curie(object_curie),
        )


#: the default header for a three-column file representing triples
HEADER = list(Triple.model_fields)


@contextmanager
def _get_file(path: str | Path, read: bool) -> Generator[TextIO, None, None]:
    path = Path(path).expanduser().resolve()
    if path.suffix == ".gz":
        yield gzip.open(path, mode="rt" if read else "wt")
    else:
        yield open(path, mode="r" if read else "w")


def write_triples(
    triples: Iterable[Triple], path: str | Path, *, header: Sequence[str] | None = None
) -> None:
    """Write triples to a file."""
    if header is None:
        header = HEADER
    with _get_file(path, read=False) as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow(header)
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
                subject=reference_cls.from_curie(subject_curie),
                predicate=reference_cls.from_curie(predicate_curie),
                object=reference_cls.from_curie(object_curie),
            )
            for subject_curie, predicate_curie, object_curie in reader
        ]


SEP = "\t"
ENCODING = "utf8"


def encode_triple(converter: Converter, triple: Triple) -> str:
    """Encode a triple with URL-safe base64 encoding."""
    return encode_delimited_uris(triple.as_uri_triple(converter))


def encode_delimited_uris(uri_triple: tuple[str, str, str]) -> str:
    """Encode a subject-predicate-object triple."""
    delimited_uris = SEP.join(uri_triple)
    return base64.urlsafe_b64encode(delimited_uris.encode(ENCODING)).decode(ENCODING)


def decode_to_uris(s: str) -> tuple[str, str, str]:
    """Decode a triple from URL-safe base64 encoding."""
    delimited_uris = base64.urlsafe_b64decode(s.encode(ENCODING)).decode(ENCODING)
    return cast(tuple[str, str, str], delimited_uris.split(SEP))


def decode_triple(converter: Converter, s: str) -> Triple:
    """Decode a triple from URL-safe base64 encoding."""
    s, p, o = decode_to_uris(s)
    return Triple(
        subject=converter.parse_uri(s, strict=True).to_pydantic(),
        predicate=converter.parse_uri(p, strict=True).to_pydantic(),
        object=converter.parse_uri(o, strict=True).to_pydantic(),
    )
