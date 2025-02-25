Typing
======

This package comes with utilities for better typing other resources.

Prefix Parsing
--------------

Let's say you have a table like this:

====== ========== ======== ======
prefix identifier name     smiles
====== ========== ======== ======
CHEBI  16236      ethanol  CCO
CHEBI  28831      propanol CCCO
CHOBI  44884      pentanol CCCCCO
====== ========== ======== ======

Note that there's a typo in the prefix on the fourth row in the prefix because it uses
``CHOBI`` instead of ``CHEBI``. In the following code, we simulate reading that file and
show where the error shows up:

.. code-block:: python

    import csv
    from pydantic import BaseModel, ValidationError
    from curies import Converter, Prefix

    converter = Converter.from_prefix_map(
        {
            "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        }
    )


    class Row(BaseModel):
        prefix: Prefix
        identifier: str
        name: str
        smiles: str


    records = [
        {"prefix": "CHEBI", "identifier": "16236", "name": "ethanol", "smiles": "CCO"},
        {"prefix": "CHEBI", "identifier": "28831", "name": "propanol", "smiles": "CCCO"},
        {"prefix": "CHOBI", "identifier": "44884", "name": "pentanol", "smiles": "CCCCCO"},
    ]

    for record in records:
        try:
            model = Row.model_validate(record, context=converter)
        except ValidationError as e:
            print(f"Issue parsing record {record}: {e}")
            continue

Note that :meth:`pydantic.BaseModel.model_validate` allows for passing a "context". The
:class:`curies.Prefix` class implements custom context handling, so if you pass a
converter, it knows how to check using prefixes in the converter.

CURIE Parsing
-------------

Let's use a similar table, now with the prefix and identifier combine into CURIEs.

=========== ======== ======
curie       name     smiles
=========== ======== ======
CHEBI:16236 ethanol  CCO
CHEBI:28831 propanol CCCO
CHOBI:44884 pentanol CCCCCO
=========== ======== ======

Note that there's a typo in the prefix on the fourth row in the prefix because it uses
``CHOBI`` instead of ``CHEBI``. In the following code, we simulate reading that file and
show where the error shows up:

.. code-block:: python

    import csv
    from pydantic import BaseModel, ValidationError
    from curies import Converter, Reference

    converter = Converter.from_prefix_map(
        {
            "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        }
    )


    class Row(BaseModel):
        curie: Reference
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
