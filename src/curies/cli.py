# -*- coding: utf-8 -*-
# type:ignore

"""Command line interface for ``curies``."""

import sys
from typing import Callable, Mapping

import click

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


def _get_app(converter: Converter, framework: str):
    if framework == "flask":
        from curies import get_flask_app

        return get_flask_app(converter)
    elif framework == "fastapi":
        from curies import get_fastapi_app

        return get_fastapi_app(converter)
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


@click.command()
@click.argument("location")
@click.option(
    "--framework",
    default="flask",
    type=click.Choice(["flask", "fastapi"]),
    show_default=True,
    help="The framework used to implement the app. Note, each requires different packages to be installed.",
)
@click.option(
    "--server",
    default="werkzeug",
    type=click.Choice(["uvicorn", "werkzeug", "gunicorn"]),
    show_default=True,
    help="The web server used to run the app. Note, each requires different packages to be installed.",
)
@click.option(
    "--format",
    type=click.Choice(list(LOADERS)),
    help="The data structure of the resolver data. Required if not giving a pre-defined converter name.",
)
@click.option(
    "--host",
    default="0.0.0.0",  # noqa:S104
    show_default=True,
    help="The host where the resolver runs",
)
@click.option(
    "--port", type=int, default=8000, show_default=True, help="The port where the resolver runs"
)
def main(location, host: str, port: int, framework: str, format: str, server: str):
    """Serve a resolver app.

    Location can either be the name of a built-in converter, a file path, or a URL.
    """
    if location in CONVERTERS:
        converter = CONVERTERS[location]()
    elif format is None:
        click.secho("--format is required with remote data", fg="red")
        return sys.exit(1)
    else:
        converter = LOADERS[format](location)

    app = _get_app(converter, framework=framework)
    _run_app(app, server=server, host=host, port=port)


if __name__ == "__main__":
    main()
