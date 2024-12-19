W3C Validation
==============
.. automodapi:: curies.w3c
   :no-inheritance-diagram:
   :no-heading:
   :include-all-objects:

In practice, some usages do not conform to these standards, often due
to encoding things that aren't _really_ supposed to be CURIEs, such as
like SMILES strings for molecules, UCUM codes for units,
or other language-like "identifiers".

Therefore, it's on the roadmap for the ``curies`` package to support
operations for validating against the W3C standards and mapping
between "loose" (i.e., un-URL-encoded) and strict (i.e., URL-encoded)
CURIEs and IRIs. In practice, this will often solve issues with special
characters like square brackets (``[`` and ``]``).

.. code-block::

     looseCURIE <-> strictCURIE
          ^.    \./.    ^
          |      X      |
          v     / \.    v
      looseURI  <->  strictURI

A first step towards accomplishing this was implemented in https://github.com/biopragmatics/curies/pull/104
by adding a ``w3c_validation`` flag to both the initialization of a :mod:`curies.Converter` as well as in the
:meth:`curies.Converter.expand` function.

Here's an example of using W3C validation during expansion:

.. code-block::

    import curies

    converter = curies.Converter.from_prefix_map({
        "smiles": "https://bioregistry.io/smiles:",
    })

    >>> converter.expand("smiles:CC(=O)NC([H])(C)C(=O)O")
    https://bioregistry.io/smiles:CC(=O)NC([H])(C)C(=O)O

    >>> converter.expand("smiles:CC(=O)NC([H])(C)C(=O)O", w3c_validation=True)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/Users/cthoyt/dev/curies/src/curies/api.py", line 1362, in expand
        raise W3CValidationError(f"CURIE is not valid under W3C spec: {curie}")
    W3CValidationError: CURIE is not valid under W3C spec: smiles:CC(=O)NC([H])(C)C(=O)O

This can also be used to extend :meth:`curies.Converter.is_curie`

.. code-block::

    import curies

    converter = curies.Converter.from_prefix_map({
        "smiles": "https://bioregistry.io/smiles:",
    })

    >>> converter.is_curie("smiles:CC(=O)NC([H])(C)C(=O)O")
    True
    >>> converter.is_curie("smiles:CC(=O)NC([H])(C)C(=O)O", w3c_validation=True)
    False

Finally, this can be used during instantiation of a converter:

.. code-block::

    import curies

    >>> curies.Converter.from_prefix_map(
    ...     {"4dn.biosource": "https://data.4dnucleome.org/biosources/"},
    ...     w3c_validation=True,
    ... )
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/Users/cthoyt/dev/curies/src/curies/api.py", line 816, in from_prefix_map
        return cls(
               ^^^^
      File "/Users/cthoyt/dev/curies/src/curies/api.py", line 527, in __init__
        raise W3CValidationError(f"Records not conforming to W3C:\n\n{msg}")
    curies.api.W3CValidationError: Records not conforming to W3C:

      - Record(prefix='4dn.biosource', uri_prefix='https://data.4dnucleome.org/biosources/', prefix_synonyms=[], uri_prefix_synonyms=[], pattern=None)


.. seealso::

    1. Discussion on the ``curies`` issue tracker about handling CURIEs that include e.g. square brackets
       and therefore don't conform to the W3C specification: https://github.com/biopragmatics/curies/issues/103
    2. Discussion on languages that shouldn't really get encoded in CURIEs, but still do:
       https://github.com/biopragmatics/bioregistry/issues/460
    3. Related to (2) - discussion on how to properly encode UCUM in CURIEs:
       https://github.com/biopragmatics/bioregistry/issues/648
