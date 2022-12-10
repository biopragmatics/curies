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
    "get_flask_app",
    "get_fastapi_router",
    "get_fastapi_app",
]

#: The code for `Unprocessable Entity <https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/422>`_
FAILURE_CODE = 422


def get_flask_blueprint(converter: Converter, **kwargs: Any) -> "flask.Blueprint":
    """Get a blueprint for :class:`flask.Flask`.

    :param converter: A converter
    :param kwargs: Keyword arguments passed through to :class:`flask.Blueprint`
    :return: A blueprint

    The following is an end-to-end example of using this function to create
    a small web resolver application.

    .. code-block::

        # flask_example.py
        from flask import Flask
        from curies import Converter, get_flask_blueprint, get_obo_converter

        # Create a converter
        converter: Converter = get_obo_converter()

        # Create a blueprint from the converter
        blueprint = get_flask_blueprint(converter)

        # Create the Flask app and mount the router
        app = Flask(__name__)
        app.register_blueprint(blueprint)

        if __name__ == "__main__":
            app.run()

    In the command line, either run your Python file directly, or via with :mod:`gunicorn`:

    .. code-block:: shell

        pip install gunicorn
        gunicorn --bind 0.0.0.0:5000 flask_example:app

    Test a request in the Python REPL. Note that Flask's development
    server runs on port 5000 by default.

    .. code-block::

        >>> import requests
        >>> requests.get("http://localhost:5000/GO:0032571").url
        'http://amigo.geneontology.org/amigo/term/GO:0032571'
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


def get_flask_app(converter: Converter) -> "flask.Flask":
    """Get a flask app."""
    from flask import Flask

    blueprint = get_flask_blueprint(converter)
    app = Flask(__name__)
    app.register_blueprint(blueprint)
    return app


def get_fastapi_router(converter: Converter, **kwargs: Any) -> "fastapi.APIRouter":
    """Get a router for :class:`fastapi.FastAPI`.

    :param converter: A converter
    :param kwargs: Keyword arguments passed through to :class:`fastapi.APIRouter`
    :return: A router

    The following is an end-to-end example of using this function to create
    a small web resolver application.

    Create a python file with your :class:`fastapi.FastAPI` instance:

    .. code-block::

        # fastapi_example.py
        from fastapi import FastAPI
        from curies import Converter, get_fastapi_router

        # Create a converter
        converter = Converter.get_obo_converter()

        # Create a router from the converter
        router = get_fastapi_router(converter)

        # Create the FastAPI and mount the router
        app = FastAPI()
        app.include_router(router)

    In the command line,, run your Python file with :mod:`uvicorn`:

    .. code-block:: shell

        pip install uvicorn
        uvicorn fastapi_example:app

    Test a request in the Python REPL. Note that :mod:`uvicorn`
    runs on port 8000 by default.

    .. code-block::

        >>> import requests
        >>> requests.get("http://localhost:8000/GO:0032571").url
        'http://amigo.geneontology.org/amigo/term/GO:0032571'
    """
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


def get_fastapi_app(converter: Converter) -> "fastapi.FastAPI":
    """Get a FastAPI app."""
    from fastapi import FastAPI

    router = get_fastapi_router(converter)
    app = FastAPI()
    app.include_router(router)
    return app
