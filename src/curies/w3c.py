"""Validation based on W3C standards.

The Worldwide Web Consortium (W3C) provides standards for
`prefixes <https://www.w3.org/TR/1999/REC-xml-names-19990114/#NT-NCName>`_ (i.e., ``NCName``),
`CURIEs <https://www.w3.org/TR/2010/NOTE-curie-20101216/>`_, and
`IRIs <https://www.ietf.org/rfc/rfc3987.txt>`_, but they are
highly obfuscated and spread across many documents.
This module attempts to operationalize these standards, along with best practices
of documentation and testing.

.. seealso::

    Some other work towards operationalizing these standards:

    - https://github.com/linkml/linkml-runtime/blob/main/linkml_runtime/utils/uri_validator.py
    - https://github.com/dgerber/rfc3987/blob/gh-archived/rfc3987.py

"""

import re

__all__ = [
    "CURIE_PATTERN",
    "LOCAL_UNIQUE_IDENTIFIER_PATTERN",
    "NCNAME_PATTERN",
    "is_w3c_curie",
    "is_w3c_prefix",
]

NCNAME_PATTERN = r"[A-Za-z_][A-Za-z0-9\.\-_]*"
"""A regex for prefixes, from https://www.w3.org/TR/1999/REC-xml-names-19990114/#NT-NCName.

.. code-block::

    prefix := NCName
    NCName := (Letter | '_') (NCNameChar)*
    NCNameChar	::=	Letter | Digit | '.' | '-' | '_'
"""

NCNAME_RE = re.compile(f"^{NCNAME_PATTERN}$")

LOCAL_UNIQUE_IDENTIFIER_PATTERN = r"(/[^\s/][^\s]*|[^\s/][^\s]*|[^\s]?)"
"""A regex for local unique identifiers in CURIEs, based on https://www.ietf.org/rfc/rfc3987.txt

This pattern was adapted from https://gist.github.com/niklasl/2506955, which sort of
implements RFC3987,
"""

LOCAL_UNIQUE_IDENTIFIER_RE = re.compile(LOCAL_UNIQUE_IDENTIFIER_PATTERN)

CURIE_PATTERN = rf"^({NCNAME_PATTERN}?:)?{LOCAL_UNIQUE_IDENTIFIER_PATTERN}$"
"""A regex for CURIEs, based on https://www.w3.org/TR/2010/NOTE-curie-20101216.

.. code-block::

    curie       :=   [ [ prefix ] ':' ] reference
    prefix      :=   NCName
    reference   :=   irelative-ref (as defined in `IRI <https://www.ietf.org/rfc/rfc3987.txt>`_)

`irelative-ref` is defined/documented in :data:`curies.w3c.LOCAL_UNIQUE_IDENTIFIER_PATTERN`.
"""

CURIE_RE = re.compile(CURIE_PATTERN)


def is_w3c_prefix(prefix: str) -> bool:
    """Return if the string is a valid prefix under the W3C specification.

    :param prefix: A string
    :return: If the string is a valid prefix under the W3C specification.

    Validation is implemented as a regular expression match against
    :data:`curies.w3c.NCNAME_PATTERN`, as defined by the W3C
    `here <https://www.w3.org/TR/1999/REC-xml-names-19990114/#NT-NCName>`_.

    Examples
    --------
    Strings containig numbers, letters, and underscores are valid prefixes.

    >>> is_w3c_prefix("GO")
    True

    The W3C specification states that the prefix '_' is reserved for use
    by languages that support RDF. For this reason, the prefix '_' SHOULD
    be avoided by authors.

    >>> is_w3c_prefix("_")
    True

    Strings starting with a number are not
    valid prefixes.

    >>> is_w3c_prefix("3dmet")

    Strings containing a colon or other
    characters are invalid

    >>> is_w3c_prefix("GO:")
    False
    """
    return bool(NCNAME_RE.match(prefix))


def _is_w3c_luid(luid: str) -> bool:
    return bool(LOCAL_UNIQUE_IDENTIFIER_RE.match(luid))


def is_w3c_curie(curie: str) -> bool:
    """Return if the string is a valid CURIE under the W3C specification.

    :param curie: A string to check if it is a valid CURIE under the W3C specification.
    :return: True if the string is a valid CURIE under the W3C specification.

    .. warning::

        This is slightly different from the :meth:`curies.Converter.is_curie` function,
        which checks if a given CURIE is valid under the extended prefix map contained
        within the converter.

        Further, the base converter is slightly more lenient than the W3C specification
        by default to allow for the inclusion of CURIEs, e.g., for SMILES strings like
        ``smiles:CC(=O)NC([H])(C)C(=O)O``. These are useful, but not technically valid
        due to their inclusion of brackets.

    Examples
    --------
    If no prefix is given, the host language chooses how to assign a default
    prefix.

    >>> is_w3c_curie(":test")
    True

    From the specification, regarding using an underscore as the prefix

        The CURIE prefix '_' is reserved for use by languages that support RDF.
        For this reason, the prefix '_' SHOULD be avoided by authors.

    >>> is_w3c_curie("_:test")
    True

    This is invalid because a CURIE prefix isn't allowed to start with
    a number. It has to start with either a letter, or an underscore.

    >>> is_w3c_curie("4cdn:test")
    False

    Empty strings are explicitly noted as being invalid.

    >>> is_w3c_curie("")
    False
    """
    if "[" in curie or "]" in curie:
        return False

    # empty curie is invalid (for now)
    if not curie.strip():
        return False

    # if there's no colon, then validate the whole thing against the LUID pattern.
    # this is because
    prefix, sep, identifier = curie.partition(":")
    if not sep:
        return _is_w3c_luid(curie)

    # it's okay for there to be no prefix in a CURIE, even though
    # the NCName definition is not itself allowed to be empty
    if not prefix:
        return _is_w3c_luid(identifier)

    return is_w3c_prefix(prefix) and _is_w3c_luid(identifier)
