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
        object="chebi:28646",
    )

    # construction with object representations of CURIEs
    triple = Triple(
        subject=Reference(prefix="mesh", identifier="C000089"),
        predicate=Reference(prefix="skos", identifier="exactMatch"),
        object=Reference(prefix="chebi", identifier="28646"),
    )

Any reference objects can be used, including ones with names:

.. code-block:: python

    from curies import NamableReference

    triple = Triple(
        subject=NamedReference(prefix="mesh", identifier="C000089", name="ammeline"),
        predicate=NamableReference(prefix="skos", identifier="exactMatch"),
        object=NamedReference(prefix="chebi", identifier="28646", name="ammeline"),
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
            "chebi": "http://purl.obolibrary.org/obo/CHEBI_",
        }
    )

    triple = Triple.from_uris(
        subject="http://id.nlm.nih.gov/mesh/C000089",
        predicate="http://www.w3.org/2004/02/skos/core#exactMatch",
        object="http://purl.obolibrary.org/obo/CHEBI_28646",
        converter=converter,
    )

###########################
 Identification of Triples
###########################

The ``rdf`` namespace supports the explicit reification of triples. This means that an
explicit identifier (typically, a blank node) can be used to refer to a triple itself,
and the ``rdf:subject``, ``rdf:predicate`` and ``rdf:object`` predicates can be used to
connect the identifier representing the triple to its respective subject, predicate, and
object components.

RDF enables explicit reification of triples with the following:

.. code-block::

    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX mesh: <http://id.nlm.nih.gov/mesh/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX chebi: <http://purl.obolibrary.org/obo/CHEBI_>

    mesh:C000089 skos:exactMatch chebi:28646 .

    [] rdf:type rdf:Statement ;
        rdf:subject mesh:C000089 ;
        rdf:predicate skos:exactMatch ;
        rdf:object chebi:28646 .

It would be nice to have an implementation-agnostic way of assigning an identifier to
the triple!

.. code-block::

    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX mesh: <http://id.nlm.nih.gov/mesh/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX chebi: <http://purl.obolibrary.org/obo/CHEBI_>
    PREFIX triple: <https://w3id.org/triple/>

    mesh:C000089 skos:exactMatch chebi:28646 .

    triple:aHR0cDovL2V4YW1wbGUub3JnLzEJaHR0cDovL2V4YW1wbGUub3JnLzIJaHR0cDovL2V4YW1wbGUub3JnLzM= rdf:type rdf:Statement ;
        rdf:subject mesh:C000089 ;
        rdf:predicate skos:exactMatch ;
        rdf:object chebi:28646 .

:func:`curies.triples.encode_triple` introduces a deterministic, reversible way of
hashing a triple to assign it an identifier.

.. code-block:: python

    import curies
    from curies import Triple, Reference
    from curies.triples import encode_triple

    converter = curies.load_prefix_map(
        {
            "ex": "http://example.org/",
        }
    )

    triple = Triple.from_uris(
        converter=converter,
        subject="http://example.org/1",
        predicate="http://example.org/2",
        object="http://example.org/3",
    )

    luid = encode_triple(converter, triple)

***********
 Algorithm
***********

1. Expand the CURIEs in a triple into URIs, encoded with UTF-8
2. String concatenate them in subject-predicate-object order, delimited by the tab
   character as a separator
3. String decode UTF-8 into bytes
4. Do a URL-safe base64 encoding of the bytes. See Python's implementation :func:`base64.urlsafe_b64encode`,
       where the alphabet uses ``-`` instead of ``+`` and ``_`` instead of ``/``.
5. Encode the result with UTF-8 to get a string.
"""

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
    """A Pydantic model for a subject-predicate-object triple.

    Triples can be constructed either from strings representing CURIEs or pre-parsed
    :class:`Reference` objects representing CURIEs.

    .. code-block:: python

        from curies import Triple, Reference

        # construction with string representations of CURIEs
        triple = Triple(
            subject="mesh:C000089",
            predicate="skos:exactMatch",
            object="chebi:28646",
        )

        # construction with object representations of CURIEs
        triple = Triple(
            subject=Reference(prefix="mesh", identifier="C000089"),
            predicate=Reference(prefix="skos", identifier="exactMatch"),
            object=Reference(prefix="chebi", identifier="28646"),
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


SEP = "\t"
ENCODING = "utf-8"
TRIPLE_PREFIX = "triple"
TRIPLE_URI_PREFIX = "https://w3id.org/triple/"


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


def decode_triple(converter: Converter, xx: str) -> Triple:
    """Decode a triple from URL-safe base64 encoding."""
    subject_uri, predicate_uri, object_uri = decode_to_uris(xx)
    return Triple.from_uris(
        subject=subject_uri,
        predicate=predicate_uri,
        object=object_uri,
        converter=converter,
    )
