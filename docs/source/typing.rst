Typing
======

This package comes with utilities for better typing other resources.

TODO:

1. demonstrate using converter to create validator using prefix, CURIE, and URI


Let's say you have a table like this:

===========  ========  ======
curie        name      smiles
===========  ========  ======
CHEBI:16236  ethanol   CCO
CHEBI:28831  propanol  CCCO
CHOBI:44884  pentanol  CCCCCO
===========  ========  ======

Note that there's a typo in the CURIE on the fourth row in the prefix because it
uses ``CHOBI`` instead of ``CHEBI``. In the following code, we simulate reading that
file and show where the error shows up:

.. code-block:: python

    import csv
    from pydantic import BaseModel, ValidationError
    from curies import CURIE, Converter

    converter = Converter.from_prefix_map({
        "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
    })

    class Row(BaseModel):
        curie: CURIE
        name: str
        smiles: str

    records = [
        {"curie": "CHEBI:16236", "name": "ethanol", "smiles": "CCO"},
        {"curie": "CHEBI:28831", "name": "propanol", "smiles": "CCCO"},
        {"curie": "CHOBI:44884", "name": "pentanol", "smiles": "CCCCCO"},
    ]

    for record in records:
        try:
            model = Row.model_validate(record, context=converter)
        except ValidationError as e:
            print(f"Issue parsing record {record}: {e}")
            continue
