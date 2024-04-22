"""Generate a JSON schema for extended prefix maps."""

import json
from pathlib import Path

from curies import Records
from curies._pydantic_compat import PYDANTIC_V1

HERE = Path(__file__).parent.resolve()
PATH = HERE.joinpath("schema.json")
TITLE = "Extended Prefix Map"
DESCRIPTION = (
    """\
An extended prefix map is a generalization of a prefix map that
includes synonyms for URI prefixes and CURIE prefixes.
""".strip()
    .replace("\n", " ")
    .replace("  ", " ")
)
URL = "https://w3id.org/biopragmatics/schema/epm.json"


def main() -> None:
    """Generate a JSON schema for extended prefix maps."""
    rv = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": URL,
    }

    if PYDANTIC_V1:
        import pydantic.schema

        # see https://docs.pydantic.dev/latest/usage/json_schema/#general-notes-on-json-schema-generation

        schema_dict = pydantic.schema.schema(
            [Records],
            title=TITLE,
            description=DESCRIPTION,
        )
    else:
        from pydantic.json_schema import models_json_schema

        _, schema_dict = models_json_schema(
            [(Records, "validation")],
            title=TITLE,
            description=DESCRIPTION,
        )

    rv.update(schema_dict)
    PATH.write_text(json.dumps(rv, indent=2) + "\n")


if __name__ == "__main__":
    main()
