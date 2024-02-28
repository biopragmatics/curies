"""
Make it possible to check a CURIE against the W3C specification.
"""

import re

__all__ = [
    "curie_is_w3c",
]

# Borrowed from https://gist.github.com/niklasl/2506955
CURIE_PATTERN = r"(([\i-[:]][\c-[:]]*)?:)?(/[^\s/][^\s]*|[^\s/][^\s]*|[^\s]?)"
CURIE_PATTERN = CURIE_PATTERN.replace(r"\i-[:]", r"_A-Za-z").replace(r"\c-[:]", r"-._:A-Za-z0-9")
CURIE_RE = re.compile(CURIE_PATTERN)


def curie_is_w3c(curie) -> bool:
    """Return if the CURIE is valid under the W3C specification."""
    return bool(CURIE_RE.match(curie))
