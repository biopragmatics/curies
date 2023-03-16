# -*- coding: utf-8 -*-
# type:ignore

"""This package comes with a built-in CLI for running a resolver web application.

.. code-block::

    $ python -m curies resolver --host 0.0.0.0 --port 8764 bioregistry

The positional argument can be one of the following:

1. A pre-defined prefix map to get from the web (bioregistry, go, obo, monarch, prefixcommons)
2. A local file path or URL to a prefix map, extended prefix map, or one of several formats. Requires specifying
   a `--format`.

The framework can be swapped to use Flask (default) or FastAPI with `--framework`. The
server can be swapped to use Werkzeug (default) or Uvicorn with `--server`. These functionalities
are also available programmatically (see :func:`get_flask_app` and :func:`get_fastapi_app`).

Similarly, there's a built-in CLI for running a mapper web application.

.. code-block::

    $ python -m curies mapper --host 0.0.0.0 --port 8764 bioregistry

The same flags and arguments are applicable.
"""

import sys
from typing import Callable, Mapping

import click

import curies
from curies import Converter, sources

__all__ = [
    "main",
]

LOADERS = {
    "jsonld": Converter.from_jsonld,
    "prefix_map": Converter.from_prefix_map,
    "extended_prefix_map": Converter.from_extended_prefix_map,
    "reverse_prefix_map": Converter.from_reverse_prefix_map,
    "priority_prefix_map": Converter.from_priority_prefix_map,
}

CONVERTERS: Mapping[str, Callable[[], Converter]] = {
    "bioregistry": sources.get_bioregistry_converter,
    "go": sources.get_go_converter,
    "monarch": sources.get_monarch_converter,
    "obo": sources.get_obo_converter,
    "prefixcommons": sources.get_prefixcommons_converter,
}


def _get_converter(location, format) -> Converter:
    if location in CONVERTERS:
        return CONVERTERS[location]()
    if format is None:
        click.secho("--format is required with remote data", fg="red")
        return sys.exit(1)
    return LOADERS[format](location)


def _get_resolver_app(converter: Converter, framework: str):
    if framework == "flask":
        return curies.get_flask_app(converter)
    elif framework == "fastapi":
        return curies.get_fastapi_app(converter)
    else:
        raise ValueError(f"Unhandled framework: {framework}")


def _get_mapper_app(converter: Converter, framework: str):
    from curies import mapping_service

    if framework == "flask":
        return mapping_service.get_flask_mapping_app(converter)
    elif framework == "fastapi":
        return mapping_service.get_fastapi_mapping_app(converter)
    else:
        raise ValueError(f"Unhandled framework: {framework}")


def _run_app(app, server, host, port):
    if server == "uvicorn":
        import uvicorn

        uvicorn.run(app, host=host, port=port)
    elif server == "werkzeug":
        app.run(host=host, port=port)
    elif server == "gunicorn":
        raise NotImplementedError
    else:
        raise ValueError(f"Unhandled server: {server}")


LOCATION_ARGUMENT = click.argument("location")
FRAMEWORK_OPTION = click.option(
    "--framework",
    default="flask",
    type=click.Choice(["flask", "fastapi"]),
    show_default=True,
    help="The framework used to implement the app. Note, each requires different packages to be installed.",
)
SERVER_OPTION = click.option(
    "--server",
    default="werkzeug",
    type=click.Choice(["werkzeug", "uvicorn", "gunicorn"]),
    show_default=True,
    help="The web server used to run the app. Note, each requires different packages to be installed.",
)
FORMAT_OPTION = click.option(
    "--format",
    type=click.Choice(list(LOADERS)),
    help="The data structure of the resolver data. Required if not giving a pre-defined converter name.",
)
HOST_OPTION = click.option(
    "--host",
    default="0.0.0.0",  # noqa:S104
    show_default=True,
    help="The host where the resolver runs",
)
PORT_OPTION = click.option(
    "--port", type=int, default=8764, show_default=True, help="The port where the resolver runs"
)


@click.group()
def main():
    """Run the `curies` CLI."""


@main.command()
@LOCATION_ARGUMENT
@FRAMEWORK_OPTION
@SERVER_OPTION
@FORMAT_OPTION
@HOST_OPTION
@PORT_OPTION
def resolver(location, host: str, port: int, framework: str, format: str, server: str):
    """Serve a resolver app.

    Location can either be the name of a built-in converter, a file path, or a URL.
    """
    converter = _get_converter(location, format)
    app = _get_resolver_app(converter, framework=framework)
    _run_app(app, server=server, host=host, port=port)


@main.command()
@LOCATION_ARGUMENT
@FRAMEWORK_OPTION
@SERVER_OPTION
@FORMAT_OPTION
@HOST_OPTION
@PORT_OPTION
def mapper(location, host: str, port: int, framework: str, format: str, server: str):
    """Serve a mapper app.

    Location can either be the name of a built-in converter, a file path, or a URL.
    """
    converter = _get_converter(location, format)
    app = _get_mapper_app(converter, framework=framework)
    _run_app(app, server=server, host=host, port=port)


if __name__ == "__main__":
    main()
