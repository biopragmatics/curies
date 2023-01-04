import json
import sys
from pathlib import Path

import click


@click.command()
@click.argument("location")
@click.option("--host", default="0.0.0.0")
@click.option("--port", type=int, default=8000)
def main(location, host: str, port: int):
    import uvicorn

    from curies import Converter, converters, get_fastapi_app

    if location in converters:
        converter = converters[location]()
    elif any(location.startswith(p) for p in ("https://", "http://", "ftp://")):
        converter = Converter.from_jsonld_url(location)  # only supports JSON-LD at the moment
    elif Path(location).is_file():
        with open(location) as file:
            converter = Converter.from_prefix_map(json.load(file))
    else:
        return sys.exit(1)
    app = get_fastapi_app(converter)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
