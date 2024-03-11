"""
Make it possible to check a CURIE against the W3C specification.

https://github.com/linkml/linkml-runtime/blob/main/linkml_runtime/utils/uri_validator.py
could serve as a good basis for extending this - adding documentation, improving readability,
and making a more detailed testing suite would make this go a long way
"""

import re

# Borrowed from https://gist.github.com/niklasl/2506955
CURIE_PATTERN = r"(([\i-[:]][\c-[:]]*)?:)?(/[^\s/][^\s]*|[^\s/][^\s]*|[^\s]?)"
CURIE_PATTERN = CURIE_PATTERN.replace(r"\i-[:]", r"_A-Za-z").replace(r"\c-[:]", r"-._:A-Za-z0-9")
CURIE_RE = re.compile(CURIE_PATTERN)