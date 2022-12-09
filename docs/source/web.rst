Resolver
========
Flask
-----
Create a python file with your :class:`flask.Flask` instance

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

    if __name__ == "":
        app.run()

Either run your Python file directly, or via with :mod:`gunicorn`:

.. code-block:: shell

    gunicorn --bind 0.0.0.0:5000 flask_example:app

Test a request in the Python shell. Note that Flask's development
server runs on port 5000 by default.

.. code-block::

    >>> import requests
    >>> requests.get("http://localhost:5000/GO:1234567").url
    'http://amigo.geneontology.org/amigo/term/GO:1234567'

FastAPI
-------
Create a python file with your :class:`fastapi.FastAPI` instance
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

Run your Python file with :mod:`uvicorn`:

.. code-block:: shell

    uvicorn fastapi_example:app

Test a request in the Python shell. Note that :mod:`uvicorn`
runs on port 8000 by default.

.. code-block::

    >>> import requests
    >>> requests.get("http://localhost:8000/GO:1234567").url
    'http://amigo.geneontology.org/amigo/term/GO:1234567'
