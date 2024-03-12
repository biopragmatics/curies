"""
Make it possible to check a CURIE against the W3C specification.

https://github.com/linkml/linkml-runtime/blob/main/linkml_runtime/utils/uri_validator.py
could serve as a good basis for extending this - adding documentation, improving readability,
and making a more detailed testing suite would make this go a long way
"""

import re

_CURIE_PREFIX_RE = r"[A-Za-z_][A-Za-z0-9\.\-_]*"
"""The definition of a prefix, from https://www.w3.org/TR/1999/REC-xml-names-19990114/#NT-NCName.

.. code-block::

    prefix := NCName
    NCName := (Letter | '_') (NCNameChar)*
    NCNameChar	::=	Letter | Digit | '.' | '-' | '_'
"""

CURIE_PREFIX_RE = re.compile(f"^{_CURIE_PREFIX_RE}$")

#: Borrowed from https://github.com/linkml/prefixmaps/blob/82bfdbc/src/prefixmaps/datamodel/context.py#L26C1-L26C60
#: Still needs adapting to see if there's an actual standard to match this to,
#: or if this is an opinionated implementation
URI_PREFIX_RE = re.compile(r"http[s]?://[\w\.\-\/]+[#/_:]$")

#: Adapted from https://gist.github.com/niklasl/2506955
_IDENTIFIER_RE = r"(/[^\s/][^\s]*|[^\s/][^\s]*|[^\s]?)"

CURIE_PATTERN = rf"({_CURIE_PREFIX_RE}?:)?{_IDENTIFIER_RE}"
CURIE_RE = re.compile(CURIE_PATTERN)
