"""Tools for URIs."""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING, Any, TypeAlias, TypeIs, Union

from pydantic import AnyUrl

if TYPE_CHECKING:
    import httpx
    import httpx2
    import rdflib

__all__ = [
    "URIType",
    "normalize_uri",
]

#: A hint for a URI
URIType: TypeAlias = Union[str, AnyUrl, "rdflib.URIRef", "httpx.URL", "httpx2.URL"]

if importlib.util.find_spec("rdflib"):
    import rdflib

    def _check_rdflib_uri(x: Any) -> TypeIs[rdflib.URIRef]:
        return isinstance(x, rdflib.URIRef)
else:

    def _check_rdflib_uri(x: Any) -> TypeIs[rdflib.URIRef]:
        return False


if importlib.util.find_spec("httpx"):
    import httpx

    def _check_httpx_url(x: Any) -> TypeIs[httpx.URL]:
        return isinstance(x, httpx.URL)
else:

    def _check_httpx_url(x: Any) -> TypeIs[httpx.URL]:
        return False


if importlib.util.find_spec("httpx2"):
    import httpx2

    def _check_httpx2_url(x: Any) -> TypeIs[httpx2.URL]:
        return isinstance(x, httpx2.URL)
else:

    def _check_httpx2_url(x: Any) -> TypeIs[httpx2.URL]:
        return False


def normalize_uri(uri: URIType) -> str:
    """Normalize a URI type."""
    if isinstance(uri, AnyUrl):
        return uri.encoded_string()
    elif _check_rdflib_uri(uri) or _check_httpx_url(uri) or _check_httpx2_url(uri):
        return str(uri)
    else:
        return uri
