# -*- coding: utf-8 -*-

"""A small demo mapping serivce."""

from curies import Converter
from curies.mapping_service import get_flask_mapping_app


def _main():
    converter = Converter.from_priority_prefix_map(
        {
            "CHEBI": [
                "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=",
                "http://identifiers.org/chebi/",
                "http://purl.obolibrary.org/obo/CHEBI_",
            ],
            "GO": ["http://purl.obolibrary.org/obo/GO_"],
            "OBO": ["http://purl.obolibrary.org/obo/"],
        }
    )
    app = get_flask_mapping_app(converter)
    app.run()


if __name__ == "__main__":
    _main()
