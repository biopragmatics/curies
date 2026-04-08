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

from .filters import (
    exclude_object_prefixes,
    exclude_prefixes,
    exclude_references,
    exclude_same_prefixes,
    exclude_subject_prefixes,
    exclude_triples,
    keep_object_prefixes,
    keep_prefixes_both,
    keep_prefixes_either,
    keep_references_both,
    keep_references_either,
    keep_subject_prefixes,
    keep_triples_by_hash,
)
from .hash_utils import encode_uri_triple, hash_triple
from .io import read_triples, write_triples
from .model import StrTriple, Triple, TriplePredicate

__all__ = [
    "StrTriple",
    "Triple",
    "TriplePredicate",
    "encode_uri_triple",
    "exclude_object_prefixes",
    "exclude_prefixes",
    "exclude_references",
    "exclude_same_prefixes",
    "exclude_subject_prefixes",
    "exclude_triples",
    "hash_triple",
    "keep_object_prefixes",
    "keep_prefixes_both",
    "keep_prefixes_either",
    "keep_references_both",
    "keep_references_either",
    "keep_subject_prefixes",
    "keep_triples_by_hash",
    "read_triples",
    "write_triples",
]
