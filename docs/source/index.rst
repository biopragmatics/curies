curies |release| Documentation
==============================
Installation
------------
The most recent release can be installed from
`PyPI <https://pypi.org/project/curies>`_ with:

.. code-block:: shell

    $ pip install curies

The most recent code and data can be installed directly from GitHub with:

.. code-block:: shell

    $ pip install git+https://github.com/cthoyt/curies.git

.. automodapi:: curies
   :no-inheritance-diagram:

CLI Usage
---------
This package comes with a built-in CLI for running a resolver web application:

.. code-block::

    $ python -m curies --host 0.0.0.0 --port 8000 bioregistry

The positional argument can be one of the following:

1. A pre-defined prefix map to get from the web (bioregistry, go, obo, monarch, prefixcommons)
2. A local file path or URL to a prefix map, extended prefix map, or one of several formats. Requires specifying
   a `--format`.

The framework can be swapped to use Flask (default) or FastAPI with `--framework`. The
server can be swapped to use Werkzeug (default) or Uvicorn with `--server`. These functionalities
are also available programmatically (see :func:`get_flask_app` and :func:`get_fastapi_app`).
