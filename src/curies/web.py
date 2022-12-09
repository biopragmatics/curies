# -*- coding: utf-8 -*-

"""A simple web service for resolving CURIEs."""

from typing import TYPE_CHECKING, Any

from .api import Converter

if TYPE_CHECKING:
    import fastapi
    import flask
    from werkzeug.wrappers import Response

__all__ = [
    "get_flask_blueprint",
    "get_fastapi_router",
]

#: The code for `Unprocessable Entity <https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/422>`_
FAILURE_CODE = 422


def get_flask_blueprint(converter: Converter, **kwargs: Any) -> "flask.Blueprint":
    """Get a blueprint appropriate for mounting on a :class:`flask.Flask` application.

    :param converter: A converter
    :param kwargs: Keyword arguments passed through to :class:`flask.Blueprint`
    :return: A blueprint

    .. code-block::

        from flask import Flask

        from curies import Converter
        from curies.web import get_blueprint

        converter: Converter = ...
        blueprint = get_blueprint(converter)
        app = Flask(__name__)
        app.register_blueprint(blueprint)
        app.run()
    """
    from flask import Blueprint, abort, redirect

    blueprint = Blueprint("metaresolver", __name__, **kwargs)

    @blueprint.route("/<prefix>:<path:identifier>")  # type:ignore
    def resolve(prefix: str, identifier: str) -> "Response":
        """Resolve a CURIE."""
        location = converter.expand_pair(prefix, identifier)
        if location is None:
            return abort(FAILURE_CODE, f"Invalid prefix: {prefix}")
        return redirect(location)

    return blueprint


def get_fastapi_router(converter: Converter, **kwargs: Any) -> "fastapi.APIRouter":
    """Get a FastAPI blueprint."""
    from fastapi import APIRouter, HTTPException, Path
    from fastapi.responses import RedirectResponse

    api_router = APIRouter(**kwargs)

    @api_router.get("/{prefix}:{identifier}")  # type:ignore
    def resolve(
        prefix: str = Path(  # noqa:B008
            title="Prefix",
            description="The Bioregistry prefix corresponding to an identifier resource.",
            example="doid",
        ),
        identifier: str = Path(  # noqa:B008
            title="Local Unique Identifier",
            description="The local unique identifier in the identifier resource referenced by the prefix.",
        ),
    ) -> RedirectResponse:
        """Resolve a CURIE."""
        location = converter.expand_pair(prefix, identifier)
        if location is None:
            raise HTTPException(status_code=FAILURE_CODE, detail=f"Invalid prefix: {prefix}")
        return RedirectResponse(location, status_code=302)

    return api_router
