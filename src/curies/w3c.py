"""
Make it possible to check a CURIE against the W3C specification.

https://github.com/linkml/linkml-runtime/blob/main/linkml_runtime/utils/uri_validator.py
could serve as a good basis for extending this - adding documentation, improving readability,
and making a more detailed testing suite would make this go a long way
"""

import re

_PREFIX_RE = r"[A-Za-z_][A-Za-z0-9\.\-_]*"
"""The definition of a prefix, from https://www.w3.org/TR/1999/REC-xml-names-19990114/#NT-NCName.

.. code-block::

    prefix := NCName
    NCName := (Letter | '_') (NCNameChar)*
    NCNameChar	::=	Letter | Digit | '.' | '-' | '_'
"""

PREFIX_RE = re.compile(f"^{_PREFIX_RE}$")


#: Borrowed from https://gist.github.com/niklasl/2506955
CURIE_PATTERN = r"(([\i-[:]][\c-[:]]*)?:)?(/[^\s/][^\s]*|[^\s/][^\s]*|[^\s]?)"
CURIE_PATTERN = CURIE_PATTERN.replace(r"\i-[:]", r"_A-Za-z").replace(r"\c-[:]", r"-._:A-Za-z0-9")
CURIE_RE = re.compile(CURIE_PATTERN)
