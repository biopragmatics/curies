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
    PREFIX CHEBI: <http://purl.obolibrary.org/obo/CHEBI_>

    mesh:C000089 skos:exactMatch CHEBI:28646 .

    [] rdf:type rdf:Statement ;
        rdf:subject mesh:C000089 ;
        rdf:predicate skos:exactMatch ;
        rdf:object CHEBI:28646 .

It would be nice to have an implementation-agnostic way of assigning an identifier to
the triple. This example imagines a namespace with the prefix ``triple`` that can host
identifiers for triples:

.. code-block::

    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX mesh: <http://id.nlm.nih.gov/mesh/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX CHEBI: <http://purl.obolibrary.org/obo/CHEBI_>
    PREFIX triple: <https://w3id.org/triple/>

    mesh:C000089 skos:exactMatch CHEBI:28646 .

    triple:36a1f9244ea7641a90987c82f33c25c0c13712ee8f48207b2a0825f8a4e4e26a rdf:type rdf:Statement ;
        rdf:subject mesh:C000089 ;
        rdf:predicate skos:exactMatch ;
        rdf:object CHEBI:28646 .

:meth:`curies.Converter.hash_triple` implements a deterministic, one-way hash of a
triple based on the algorithm in https://ts4nfdi.github.io/mapping-sameness-identifier:

.. code-block:: python

    import curies
    from curies import Triple, Converter

    converter = curies.load_prefix_map(
        {
            "mesh": "http://id.nlm.nih.gov/mesh/",
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        }
    )
    triple = Triple(
        subject="mesh:C000089",
        predicate="skos:exactMatch",
        object="CHEBI:28646",
    )
    triple_id = converter.hash_triple(triple)
    assert triple_id == "36a1f9244ea7641a90987c82f33c25c0c13712ee8f48207b2a0825f8a4e4e26a"
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import NamedTuple, TextIO

from pydantic import BaseModel, ConfigDict
from pystow.utils import safe_open_reader, safe_open_writer
from typing_extensions import Self

from .api import Converter, Reference

__all__ = [
    "StrTriple",
    "Triple",
    "hash_triple",
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


def hash_triple(converter: Converter, triple: Triple) -> str:
    """Encode a triple with URL-safe base64 encoding.

    :param converter: A converter
    :param triple: A triple of CURIE objects

    :returns: An encoded triple of URIs

    .. seealso::

        https://ts4nfdi.github.io/mapping-sameness-identifier/

    >>> converter = curies.load_prefix_map(
    ...     {
    ...         "mesh": "http://id.nlm.nih.gov/mesh/",
    ...         "skos": "http://www.w3.org/2004/02/skos/core#",
    ...         "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
    ...     }
    ... )
    >>> triple = Triple(subject="mesh:C000089", predicate="skos:exactMatch", object="CHEBI:28646")
    >>> hash_triple(converter, triple)
    '36a1f9244ea7641a90987c82f33c25c0c13712ee8f48207b2a0825f8a4e4e26a'
    """
    return encode_delimited_uris(triple.as_uri_triple(converter))


def encode_delimited_uris(uri_triple: tuple[str, str, str]) -> str:
    """Encode a subject-predicate-object triple.

    :param uri_triple: A triple of URIs represented as strings

    :returns: An encoded triple of URIs

    .. seealso::

        https://ts4nfdi.github.io/mapping-sameness-identifier/

    >>> encode_delimited_uris(
    ...     (
    ...         "http://id.nlm.nih.gov/mesh/C000089",
    ...         "http://www.w3.org/2004/02/skos/core#exactMatch",
    ...         "http://purl.obolibrary.org/obo/CHEBI_28646",
    ...     )
    ... )
    '36a1f9244ea7641a90987c82f33c25c0c13712ee8f48207b2a0825f8a4e4e26a'
    """
    delimited_uris = " ".join(uri_triple)
    digest = hashlib.sha256(delimited_uris.encode("utf-8")).hexdigest()
    return digest
