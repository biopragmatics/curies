import json
import sys
from pathlib import Path
from typing import Callable, Mapping

import click
from more_click import run_app
from curies import Converter, sources

REMOTE_LOADERS = {
    "jsonld": Converter.from_jsonld_url,
    "prefix_map": Converter.from_prefix_map_url,
    "extended_prefix_map": Converter.from_extended_prefix_map_url,
    "reverse_prefix_map": Converter.from_reverse_prefix_map_url,
    "priority_prefix_map": Converter.from_priority_prefix_map_url,
}
LOCAL_LOADERS = {
    "jsonld": Converter.from_jsonld,
    "prefix_map": Converter.from_prefix_map,
    "extended_prefix_map": Converter.from_extended_prefix_map,
    "reverse_prefix_map": Converter.from_reverse_prefix_map,
    "priority_prefix_map": Converter.from_priority_prefix_map,
}

CONVERTERS: Mapping[str, Callable[..., Converter]] = {
    "bioregistry": sources.get_bioregistry_converter,
    "go": sources.get_go_converter,
    "monarch": sources.get_monarch_converter,
    "obo": sources.get_obo_converter,
    "prefixcommons": sources.get_prefixcommons_converter,
}


def _get_app(converter, backend):
    if backend == "flask":
        from curies import get_flask_app

        return get_flask_app(converter)
    elif backend == "fastapi":
        from curies import get_fastapi_app

        return get_fastapi_app(converter)
    else:
        raise ValueError(f"Unhandled backend: {backend}")


def _run_app(app, runner, host, port):
    if runner == "uvicorn":
        import uvicorn
        uvicorn.run(app, host=host, port=port)
    elif runner == "werkzeug":
        app.run(host=host, port=port)
    elif runner == "gunicorn":
        raise NotImplementedError
    else:
        raise ValueError


@click.command()
@click.argument("location")
@click.option("--backend", default="flask", type=click.Choice(["flask", "fastapi"]), show_default=True)
@click.option("--runner", default="uvicorn", type=click.Choice(["uvicorn", "werkzeug", "gunicorn"]), show_default=True)
@click.option("--format", type=click.Choice(list(LOCAL_LOADERS)))
@click.option("--host", default="0.0.0.0")
@click.option("--port", type=int, default=8000)
def main(location, host: str, port: int, backend: str, format: str, runner):
    if location in CONVERTERS:
        converter = CONVERTERS[location]()
    elif format is None:
        click.secho('--format is required with remote data', fg="red")
        return sys.exit(1)
    elif any(location.startswith(p) for p in ("https://", "http://", "ftp://")):
        converter = REMOTE_LOADERS[format](location)
    elif Path(location).is_file():
        with open(location) as file:
            converter = LOCAL_LOADERS[format](json.load(file))
    else:
        return sys.exit(1)

    app = _get_app(converter, backend=backend)
    _run_app(app, runner=runner, host=host, port=port)


if __name__ == "__main__":
    main()
