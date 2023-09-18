Reconciliation
==============
.. todo::

    - What is reconciliation?
    - Why do we need to do it?

      - When we want to build on a pre-existing extended prefix map, but have a couple use-case-specific overrides.
        This enables us to build on existing content instead of re-inventing the wheel over and over

- **Remapping** is when a given CURIE or URI prefix is replaced with another
- **Rewiring** is when the correspondence between a CURIE prefix and URI prefix is updated


Throughout this document, we're going to use the following extended prefix map as an example

.. code-block:: json

    [
        {"prefix": "a", "uri_prefix": "https://example.org/a/", "prefix_synonyms": ["a1"]},
        {"prefix": "b", "uri_prefix": "https://example.org/b/"}
    ]


CURIE Prefix Remapping
----------------------
CURIE prefix remapping is configured by a mapping from existing CURIE prefixes to new CURIE prefixes.
The following rules are applied for each pair of old/new prefixes:

1. New prefix exists
~~~~~~~~~~~~~~~~~~~~
If the new prefix appears as a prefix synonym in the record corresponding to the old prefix, they are swapped.
This means applying the CURIE prefix remapping ``{"a": "a1"}`` results in the following

.. code-block:: json

    [
        {"prefix": "a1", "uri_prefix": "https://example.org/a/", "prefix_synonyms": ["a"]},
        {"prefix": "b", "uri_prefix": "https://example.org/b/"}
    ]

If the new prefix appears as a preferred prefix or prefix synonym for any other record, one of two things can happen:

1. Do nothing (lenient)
2. Raise an exception (strict)

This means applying the CURIE prefix remapping ``{"a": "b"}`` results in either no change or an exception being raised.

2. New prefix doesn't exist, old prefix is a preferred prefix
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If the old prefix appears in a record in the extended prefix map as a preferred prefix:

1. Replace the record's preferred prefix with the new prefix
2. Add the record's old preferred prefix to the record's prefix synonyms

This means applying the CURIE prefix remapping ``{"a": "c"}`` results in the following

.. code-block:: json

    [
        {"prefix": "c", "uri_prefix": "https://example.org/a/", "prefix_synonyms": ["a", "a1"]},
        {"prefix": "b", "uri_prefix": "https://example.org/b/"}
    ]

Similarly, if the old prefix appears in a record in the extended prefix map as a prefix synonym, do the same.
This means applying the CURIE prefix remapping ``{"a1": "c"}`` results in the following

.. code-block:: json

    [
        {"prefix": "c", "uri_prefix": "https://example.org/a/", "prefix_synonyms": ["a", "a1"]},
        {"prefix": "b", "uri_prefix": "https://example.org/b/"}
    ]

3. New prefix doesn't exist, old prefix doesn't exist
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If neither the old prefix nor new prefix appear in the extended prefix maps, one of two things can happen:

1. Do nothing (lenient)
2. Raise an exception (strict)

Prefix Rewiring
---------------
Prefix rewiring is configured by a mapping from existing CURIE prefixes to new URI prefixes.
The following rules are applied for each pair of CURIE prefix/URI prefix:

1. CURIE prefix doesn't exist
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If the CURIE prefix doesn't exist in the extended prefix map, then the pair is simply appended.
This means applying the rewiring ``{"c": "https://example.org/c"}`` results in the following

.. code-block:: json

    [
        {"prefix": "a", "uri_prefix": "https://example.org/a/", "prefix_synonyms": ["a1"]},
        {"prefix": "b", "uri_prefix": "https://example.org/b/"},
        {"prefix": "c", "uri_prefix": "https://example.org/c/"}
    ]

2. URI prefix exists
~~~~~~~~~~~~~~~~~~~~
If the URI prefix appears as either a preferred URI prefix or as a URI prefix synonym in
any record in the extended prefix map, do one of the following:

1. Do nothing (lenient)
2. Raise an exception (strict)


3. CURIE prefix exists, URI prefix doesn't exist
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1. Replace the record's preferred URI prefix with the new URI prefix
2. Add the record's old preferred URI prefix to the record's URI prefix synonyms

This means applying the rewiring ``{"b": "https://example.org/b_new/"}`` results in the following

.. code-block:: json

    [
        {"prefix": "a", "uri_prefix": "https://example.org/a/", "prefix_synonyms": ["a1"]},
        {"prefix": "b", "uri_prefix": "https://example.org/b_new/", "uri_prefix_synonyms": ["https://example.org/b/"]}
    ]

Undefined
~~~~~~~~~
1. What to do if the prefix given is a prefix synonym in an existing record?
