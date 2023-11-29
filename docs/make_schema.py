import pydantic
import pydantic.schema
from typing import List

from pydantic import BaseModel, ConfigDict

from curies import Record
from pathlib import Path
import json

HERE = Path(__file__).parent.resolve()
PATH = HERE.joinpath("path.json")
TITLE = "Extended Prefix Map"
DESCRIPTION = ""


class Records(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    class Config:
        arbitrary_types_allowed = True

    __root__ = List[Record]


def main():
    rv = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://bioregistry.io/schema.json",
    }

    try:
        # see https://docs.pydantic.dev/latest/usage/json_schema/#general-notes-on-json-schema-generation
        from pydantic.json_schema import models_json_schema
    except ImportError:
        schema_dict = pydantic.schema.schema(
            [Records],
            title=TITLE,
            description=DESCRIPTION,
        )
    else:
        _, schema_dict = models_json_schema(
            [(Records, "validation")],
            title=TITLE,
            description=DESCRIPTION,
        )
    rv.update(schema_dict)

    PATH.write_text(json.dumps(rv, indent=2))


if __name__ == "__main__":
    main()
