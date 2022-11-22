# -*- coding: utf-8 -*-

"""A simple web service for resolving CURIEs."""

from typing import TYPE_CHECKING

from .api import Converter

if TYPE_CHECKING:
    import flask

__all__ = [
    "get_blueprint",
]

#: The code for `Unprocessable Entity <https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/422>`_
FAILURE_CODE = 422


def get_blueprint(converter: Converter, **kwargs) -> "flask.Blueprint":
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

    @blueprint.route("/<prefix>:<path:identifier>")
    def resolve(prefix: str, identifier: str):
        """Resolve a CURIE."""
        location = converter.expand_pair(prefix, identifier)
        if location is not None:
            return redirect(location)
        return abort(FAILURE_CODE)

    return blueprint
