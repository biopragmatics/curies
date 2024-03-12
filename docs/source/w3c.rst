W3C Compliance
==============
The Worldwide Web Consortium (W3C) provides standards for
`prefixes <https://www.w3.org/TR/1999/REC-xml-names-19990114/#NT-NCName>`_ (i.e., ``NCName``),
`CURIEs <https://www.w3.org/TR/2010/NOTE-curie-20101216/>`_, and
`IRIs <https://www.ietf.org/rfc/rfc3987.txt>`_, but they are
highly obfuscated and spread across many documents.

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

.. seealso::

    1. Discussion on the ``curies`` issue tracker about handling CURIEs that include e.g. square brackets
       and therefore don't conform to the W3C specification: https://github.com/biopragmatics/curies/issues/103
    2. Discussion on languages that shouldn't really get encoded in CURIEs, but still do:
       https://github.com/biopragmatics/bioregistry/issues/460
    3. Related to (2) - discussion on how to properly encode UCUM in CURIEs:
       https://github.com/biopragmatics/bioregistry/issues/648
