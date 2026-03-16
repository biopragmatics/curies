"""Similarly to how the :mod:`curies` package enables the semantic representation of references (i.e., as CURIEs) with the :class:`curies.Reference` class, it enables the representation of semantic triples (i.e., as subject-predicate-object triples of CURIEs) with the :class:`curies.Triple` class.

######################
 Constructing Triples
######################

Triples can be constructed either from strings representing CURIEs or pre-parsed
:class:`Reference` objects representing CURIEs.

.. code-block:: python

    from curies import Triple, Reference

    # construction with string representations of CURIEs
    triple = Triple(
        subject="mesh:C000089",
        predicate="skos:exactMatch",
        object="CHEBI:28646",
    )

    # construction with object representations of CURIEs
    triple = Triple(
        subject=Reference(prefix="mesh", identifier="C000089"),
        predicate=Reference(prefix="skos", identifier="exactMatch"),
        object=Reference(prefix="CHEBI", identifier="28646"),
    )

Any reference objects can be used, including ones with names:

.. code-block:: python

    from curies import NamableReference

    triple = Triple(
        subject=NamedReference(prefix="mesh", identifier="C000089", name="ammeline"),
        predicate=NamableReference(prefix="skos", identifier="exactMatch"),
        object=NamedReference(prefix="CHEBI", identifier="28646", name="ammeline"),
    )

The :class:`Triple` interface does not enforce any CURIE validation. The
:meth:`Triple.from_uris` constructor implicitly performs validation against a converter
while parsing.

.. code-block:: python

    from curies import Triple, Reference, Converter

    converter = curies.load_prefix_map(
        {
            "mesh": "http://id.nlm.nih.gov/mesh/",
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        }
    )

    triple = Triple.from_uris(
        subject="http://id.nlm.nih.gov/mesh/C000089",
        predicate="http://www.w3.org/2004/02/skos/core#exactMatch",
        object="http://purl.obolibrary.org/obo/CHEBI_28646",
        converter=converter,
    )
"""

from __future__ import annotations

import base64
import csv
import gzip
from collections.abc import Generator, Iterable, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import NamedTuple, TextIO

from pydantic import BaseModel, ConfigDict
from typing_extensions import Self

from .api import Converter, Reference

__all__ = [
    "StrTriple",
    "Triple",
    "read_triples",
    "write_triples",
]


class StrTriple(NamedTuple):
    """A triple of curies."""

    subject: str
    predicate: str
    object: str


class Triple(BaseModel):
    """A Pydantic model for a subject-predicate-object triple.

    Triples can be constructed either from strings representing CURIEs or pre-parsed
    :class:`Reference` objects representing CURIEs.

    .. code-block:: python

        from curies import Triple, Reference

        # construction with string representations of CURIEs
        triple = Triple(
            subject="mesh:C000089",
            predicate="skos:exactMatch",
            object="CHEBI:28646",
        )

        # construction with object representations of CURIEs
        triple = Triple(
            subject=Reference(prefix="mesh", identifier="C000089"),
            predicate=Reference(prefix="skos", identifier="exactMatch"),
            object=Reference(prefix="CHEBI", identifier="28646"),
        )

    .. note::

        It's up to you to validate your CURIEs are semantically sound, e.g., against the
        :mod:`bioregistry`.
    """

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
            converter.expand_reference(self.subject, strict=True),
            converter.expand_reference(self.predicate, strict=True),
            converter.expand_reference(self.object, strict=True),
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

    @classmethod
    def from_uris(
        cls,
        subject: str,
        predicate: str,
        object: str,
        *,
        converter: Converter,
        reference_cls: type[Reference] = Reference,
    ) -> Self:
        """Construct a triple from three URI strings."""
        return cls(
            subject=reference_cls.from_reference(converter.parse_uri(subject, strict=True)),
            predicate=reference_cls.from_reference(converter.parse_uri(predicate, strict=True)),
            object=reference_cls.from_reference(converter.parse_uri(object, strict=True)),
        )


#: the default header for a three-column file representing triples
HEADER = list(Triple.model_fields)


@contextmanager
def _get_file(path: str | Path, read: bool) -> Generator[TextIO, None, None]:
    path = Path(path).expanduser().resolve()
    if path.suffix == ".gz":
        with gzip.open(path, mode="rt" if read else "wt") as file:
            yield file
    else:
        with open(path, mode="r" if read else "w") as file:
            yield file


def write_triples(
    triples: Iterable[Triple], path: str | Path, *, header: Sequence[str] | None = None
) -> None:
    """Write triples as a three-column TSV file."""
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
    """Read triples from a three-column TSV file."""
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
