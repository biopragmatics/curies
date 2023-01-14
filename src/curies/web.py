# -*- coding: utf-8 -*-

"""A simple web service for resolving CURIEs."""

from typing import TYPE_CHECKING, Any, Mapping, Optional

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


def get_flask_app(
    converter: Converter,
    blueprint_kwargs: Optional[Mapping[str, Any]] = None,
    flask_kwargs: Optional[Mapping[str, Any]] = None,
    register_kwargs: Optional[Mapping[str, Any]] = None,
) -> "flask.Flask":
    """Get a Flask app.

    :param converter: A converter
    :param blueprint_kwargs: Keyword arguments passed through to :class:`flask.Blueprint`
    :param flask_kwargs: Keyword arguments passed through to :class:`flask.Flask`
    :param register_kwargs: Keyword arguments passed through to :meth:`flask.Flask.register_blueprint`
    :return: A Flask app

    .. seealso:: This function wraps :func:`get_flask_blueprint`

    The following is an end-to-end example of using this function to create
    a small web resolver application.

    .. code-block::

        # flask_example.py
        from flask import Flask
        from curies import Converter, get_flask_app, get_obo_converter

        # Create a converter
        converter: Converter = get_obo_converter()

        # Create the Flask app
        app: Flask = get_flask_app(converter)

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
    from flask import Flask

    blueprint = get_flask_blueprint(converter, **(blueprint_kwargs or {}))
    app = Flask(__name__, **(flask_kwargs or {}))
    app.register_blueprint(blueprint, **(register_kwargs or {}))
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


def get_fastapi_app(
    converter: Converter,
    router_kwargs: Optional[Mapping[str, Any]] = None,
    fastapi_kwargs: Optional[Mapping[str, Any]] = None,
    include_kwargs: Optional[Mapping[str, Any]] = None,
) -> "fastapi.FastAPI":
    """Get a FastAPI app.

    :param converter: A converter
    :param router_kwargs: Keyword arguments passed through to :class:`fastapi.APIRouter`
    :param fastapi_kwargs: Keyword arguments passed through to :class:`fastapi.FastAPI`
    :param include_kwargs: Keyword arguments passed through to :meth:`fastapi.FastAPI.include_router`
    :return: A FastAPI app

    .. seealso:: This function wraps :func:`get_fastapi_router`

    The following is an end-to-end example of using this function to create
    a small web resolver application.

    Create a python file with your :class:`fastapi.FastAPI` instance:

    .. code-block::

        # fastapi_example.py
        from fastapi import FastAPI
        from curies import Converter, get_fastapi_app

        # Create a converter
        converter = Converter.get_obo_converter()

        # Create the FastAPI
        app: FastAPI = get_fastapi_app(converter)

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
    from fastapi import FastAPI

    router = get_fastapi_router(converter, **(router_kwargs or {}))
    app = FastAPI(**(fastapi_kwargs or {}))
    app.include_router(router, **(include_kwargs or {}))
    return app
