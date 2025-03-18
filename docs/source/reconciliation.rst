Reconciliation
==============

Reconciliation is the high-level process of modifying an (extended) prefix map with
domain-specific rules. This is important as it allows for building on existing
(extended) prefix maps without having to start from scratch. Further, storing the rules
to transform an existing prefix map allows for high-level discussion about the
differences and their reasons.

As a specific example, the `Bioregistry <https://bioregistry.io/>`_ uses ``snomedct`` as
a preferred prefix for the Systematized Nomenclature of Medicine - Clinical Terms
(SNOMED-CT). The OBO Foundry community prefers to use ``SCTID`` as the preferred prefix
for this resource. Rather than maintaining a different extended prefix map than the
Bioregistry, the OBO Foundry community could enumerate its preferred modifications to
the base (extended) prefix map, then create its prefix map by transforming the
Bioregistry's.

Similarly, a consumer of the OBO Foundry prefix map who's implementing a resolver might
want to override the URI prefix associated with the `Ontology of Vaccine Adverse Events
(OVAE) <https://bioregistry.io/registry/ovae>`_ to point towards the Ontology Lookup
Service instead of the default OntoBee.

There are two operations that are useful for transforming an existing (extended) prefix
map:

1. **Remapping** is when a given CURIE prefix or URI prefix is replaced with another.
   See :func:`curies.remap_curie_prefixes` and :func:`curies.remap_uri_prefixes`.
2. **Rewiring** is when the correspondence between a CURIE prefix and URI prefix is
   updated. See :func:`curies.rewire`.

Throughout this document, we're going to use the following extended prefix map as an
example to illustrate how these operations work from a high level.

.. code-block:: json

    [
        {"prefix": "a", "uri_prefix": "https://example.org/a/", "prefix_synonyms": ["a1"]},
        {"prefix": "b", "uri_prefix": "https://example.org/b/"}
    ]

CURIE Prefix Remapping
----------------------

CURIE prefix remapping is configured by a dictionary from existing CURIE prefixes to new
CURIE prefixes. The following rules are applied for each pair of old/new prefixes:

1. New prefix exists
~~~~~~~~~~~~~~~~~~~~

If the new prefix appears as a prefix synonym in the record corresponding to the old
prefix, they are swapped. This means applying the CURIE prefix remapping ``{"a": "a1"}``
results in the following

.. code-block:: json

    [
        {"prefix": "a1", "uri_prefix": "https://example.org/a/", "prefix_synonyms": ["a"]},
        {"prefix": "b", "uri_prefix": "https://example.org/b/"}
    ]

If the new prefix appears as a preferred prefix or prefix synonym for any other record,
one of two things can happen:

1. Do nothing (lenient)
2. Raise an exception (strict)

This means applying the CURIE prefix remapping ``{"a": "b"}`` results in either no
change or an exception being raised.

2. New prefix doesn't exist, old prefix exists
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the old prefix appears in a record in the extended prefix map as a preferred prefix:

1. Replace the record's preferred prefix with the new prefix
2. Add the record's old preferred prefix to the record's prefix synonyms

This means applying the CURIE prefix remapping ``{"a": "c"}`` results in the following

.. code-block:: json

    [
        {"prefix": "c", "uri_prefix": "https://example.org/a/", "prefix_synonyms": ["a", "a1"]},
        {"prefix": "b", "uri_prefix": "https://example.org/b/"}
    ]

Similarly, if the old prefix appears in a record in the extended prefix map as a prefix
synonym, do the same. This means applying the CURIE prefix remapping ``{"a1": "c"}``
results in the following

.. code-block:: json

    [
        {"prefix": "c", "uri_prefix": "https://example.org/a/", "prefix_synonyms": ["a", "a1"]},
        {"prefix": "b", "uri_prefix": "https://example.org/b/"}
    ]

3. New prefix doesn't exist, old prefix doesn't exist
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If neither the old prefix nor new prefix appear in the extended prefix maps, one of two
things can happen:

1. Do nothing (lenient)
2. Raise an exception (strict)

Transitive CURIE Prefix Remapping
---------------------------------

There's a special case of CURIE prefix remapping where one prefix is supposed to
overwrite another. For example, in the Bioregistry, the `Gene Expression Omnibus
<https://www.ncbi.nlm.nih.gov/geo/>`_ is given the prefix ``geo`` and the `Geographical
Entity Ontology <https://obofoundry.org/ontology/geo>`_ is given the prefix ``geogeo``.
OBO Foundry users will want to rename the Gene Expression Omnibus record to something
else like ``ncbi.geo`` and rename ``geogeo`` to ``geo``. Taken by themselves, these two
operations would not accomplish the desired results:

1. Remapping with ``{"geo": "ncbi.geo"}`` would retain ``geo`` as a CURIE prefix synonym
2. Remapping with ``{"geogeo": "geo"}`` would not change the mapping as ``geo`` is
   already part of a different record.

The :func:`curies.remap_curie_prefixes` implements special logic to identify scenarios
where two (or more) remappings are dependent (we're calling these *transitive
remappings*) and apply them in the expected way. Therefore, we see the following

.. code-block:: python

    from curies import Converter, Record, remap_curie_prefixes

    converter = Converter(
        [
            Record(
                prefix="geo",
                uri_prefix="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=",
            ),
            Record(prefix="geogeo", uri_prefix="http://purl.obolibrary.org/obo/GEO_"),
        ]
    )
    remapping = {"geo": "ncbi.geo", "geogeo": "geo"}
    converter = remap_curie_prefixes(converter, curie_remapping)

    assert converter.records == [
        Record(
            prefix="geo",
            prefix_synonyms=["geogeo"],
            uri_prefix="http://purl.obolibrary.org/obo/GEO_",
        ),
        Record(
            prefix="ncbi.geo",
            uri_prefix="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=",
        ),
    ]

``geogeo`` is maintained as a CURIE prefix synonym for the Geographical Entity
Ontology's record. Synonyms of Gene Expression Omnibus would also be retained.

.. note::

    This is not the same as an "overwrite" which would delete the original ``geo``
    operation. This package expects that you give a new CURIE prefix to all
    "overwritten" records such that no records are lost.

.. warning::

    Primary prefixes must be used when doing transitive remappings. Handling synonyms
    proved to be too complex. Therefore, if you use a CURIE prefix remapping like in the
    following, you will get an exception.

    .. code-block::

        converter = Converter([
            Record(
                prefix="geo",
                prefix_synonyms=["ggg"],
                uri_prefix="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=",
            ),
            Record(prefix="geogeo", uri_prefix="http://purl.obolibrary.org/obo/GEO_"),
        ])
        curie_remapping = {"ggg": "ncbi.geo", "geogeo": "geo"}

URI Prefix Remapping
--------------------

URI prefix remapping is configured by a mapping from existing URI prefixes to new URI
prefixes. The rules work exactly the same as with CURIE prefix remapping, but for the
:data:`curies.Record.uri_prefix` and :data:`curies.Record.uri_prefix_synonyms` fields.

Rewiring
--------

Rewiring is configured by a dictionary from existing CURIE prefixes to new URI prefixes.
The following rules are applied for each pair of CURIE prefix/URI prefix:

CURIE prefix exists, URI prefix doesn't exist
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the CURIE prefix appears as either the preferred prefix or a prefix synonym, do the
following

1. Replace the record's preferred URI prefix with the new URI prefix
2. Add the record's old preferred URI prefix to the record's URI prefix synonyms

This means applying the rewiring ``{"b": "https://example.org/b_new/"}`` results in the
following

.. code-block:: json

    [
        {"prefix": "a", "uri_prefix": "https://example.org/a/", "prefix_synonyms": ["a1"]},
        {"prefix": "b", "uri_prefix": "https://example.org/b_new/", "uri_prefix_synonyms": ["https://example.org/b/"]}
    ]

CURIE prefix exists, URI prefix exists
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the CURIE prefix and URI prefix both appear in the extended prefix map, there are
three possibilities.

1. If they are in the same record and the URI prefix is already the preferred prefix,
   then nothing needs to be done. This means that the rewiring ``{"a":
   "https://example.org/a/"}`` results in no change.
2. If they are in the same record and the URI prefix is a URI prefix synonym, then the
   URI prefix synonym is swapped with the preferred URI prefix. This means if we have
   the following extended prefix map

   .. code-block:: json

       [
           {"prefix": "a", "uri_prefix": "https://example.org/a/", "uri_prefix_synonyms": ["https://example.org/a1/"]}
       ]

   and apply ``{"a": "https://example.org/a1/"}``, we get the following result

   .. code-block:: json

       [
           {"prefix": "a", "uri_prefix": "https://example.org/a/", "uri_prefix_synonyms": ["https://example.org/a1/"]}
       ]

3. If they appear in different records, then either do nothing (lenient) or raise an
   exception (strict)

CURIE prefix doesn't exist, URI prefix doesn't exist
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the CURIE prefix doesn't appear in the extended prefix map, then nothing is done.
Adding fully novel content to the extended prefix map can be done with other operations
such as :meth`:curies.Converter.add_record` or :func:`curies.chain`.

.. note::

    There is discussion whether this case could be extended with the following: if the
    CURIE prefix doesn't exist in the extended prefix map, then the pair is simply
    appended. This means applying the rewiring ``{"c": "https://example.org/c"}``
    results in the following

    .. code-block:: json

        [
            {"prefix": "a", "uri_prefix": "https://example.org/a/", "prefix_synonyms": ["a1"]},
            {"prefix": "b", "uri_prefix": "https://example.org/b/"},
            {"prefix": "c", "uri_prefix": "https://example.org/c/"}
        ]

    This is not included in the base implementation because it conflates the job of
    "rewiring" with appending to the extended prefix map

CURIE prefix doesn't exist, URI prefix exists
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the URI prefix appears as either a preferred URI prefix or as a URI prefix synonym in
any record in the extended prefix map, do one of the following:

1. Do nothing (lenient)
2. Raise an exception (strict)
