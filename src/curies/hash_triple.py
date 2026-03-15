"""Encode and decode triples with URL-safe base64 encoding."""

import base64
from typing import cast

from .api import Converter
from .triples import Triple

__all__ = ["decode_triple", "encode_triple"]

SEP = "\t"
ENCODING = "utf8"


def encode_triple(converter: Converter, triple: Triple) -> str:
    """Encode a triple with URL-safe base64 encoding."""
    return encode_delimited_uris(
        cast(
            tuple[str, str, str],
            tuple(converter.expand(part, strict=True) for part in triple.as_str_triple()),
        )
    )


def encode_delimited_uris(uri_triple: tuple[str, str, str]) -> str:
    """Encode a subject-predicate-object triple."""
    delimited_uris = SEP.join(uri_triple)
    return base64.urlsafe_b64encode(delimited_uris.encode(ENCODING)).decode(ENCODING)


def decode_to_uris(s: str) -> tuple[str, str, str]:
    """Decode a triple from URL-safe base64 encoding."""
    delimited_uris = base64.urlsafe_b64decode(s.encode(ENCODING)).decode(ENCODING)
    return cast(tuple[str, str, str], delimited_uris.split(SEP))


def decode_triple(converter: Converter, s: str) -> Triple:
    """Decode a triple from URL-safe base64 encoding."""
    s, p, o = decode_to_uris(s)
    return Triple(
        subject=converter.parse_uri(s, strict=True).to_pydantic(),
        predicate=converter.parse_uri(p, strict=True).to_pydantic(),
        object=converter.parse_uri(o, strict=True).to_pydantic(),
    )
