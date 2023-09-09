Getting Started
===============
Loading a Context
-----------------
There are several ways to load a context with this package, including:

1. pre-defined contexts
2. contexts encoded in the standard prefix map format
3. contexts encoded in the standard JSON-LD context format
4. contexts encoded in the extended prefix map format

Loading a pre-defined context
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
There exist many registries of semantic spaces that include CURIE
prefixes, URI prefixes, sometimes synonyms, and other associated
metadata. The Bioregistry provides a
`detailed overview <https://bioregistry.io/related>`_ of the registries available.
This package exposes a few high quality registries that are internally consistent
(i.e., are bijective).

==============  ==========================================
Name            Function
==============  ==========================================
Bioregistry     :func:`curies.get_bioregistry_converter`
OBO Foundry     :func:`curies.get_obo_converter`
Prefix Commons  :func:`curies.get_prefixcommons_converter`
Monarch         :func:`curies.get_monarch_converter`
Gene Ontology   :func:`curies.get_go_converter`
==============  ==========================================

These functions can be called directly to instantiate the :class:`curies.Converter`
class, which is used for compression, expansion, standardization, and other operations
below.

.. code-block:: python

    import curies

    # Uses the Bioregistry, an integrative, comprehensive registry
    bioregistry_converter = curies.get_bioregistry_converter()

    # Uses the OBO Foundry, a registry of ontologies
    obo_converter = curies.get_obo_converter()

    # Uses the Monarch Initative's project-specific context
    monarch_converter = curies.get_monarch_converter()

Loading Prefix Maps
~~~~~~~~~~~~~~~~~~~
A prefix map is a dictionary whose keys are CURIE prefixes and values are URI prefixes. An abridged example
using OBO Foundry preferred CURIE prefixes and URI prefixes is

.. code-block:: json

   {
       "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
       "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
       "GO": "http://purl.obolibrary.org/obo/GO_"
   }

Prefix maps can be loaded using the :func:`curies.load_prefix_map`. First,
a prefix map can be loaded directly from a Python data structure like in

.. code-block:: python

    import curies

    prefix_map = {
        "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_"
    }
    converter = curies.load_prefix_map(data)

This function also accepts a string with a HTTP, HTTPS, or FTP path to a remote file as well as a local file path.

.. warning::

    Ideally, prefix maps are *bijective*, meaning that both the keys and values are unique.
    The Python dictionary data structure ensures that keys are unique, but sometimes values are repeated. For example,
    the CURIE prefixes ``DC`` and ``DCTERMS`` are often used interchangeably with the URI prefix for
    the `Dublin Core Metadata Iniative Terms <https://www.dublincore.org/specifications/dublin-core/dcmi-terms>`_.
    Therefore, many prefix maps are not bijective like

    .. code-block:: json

       {
           "DC": "http://purl.org/dc/terms/",
           "DCTERMS": "http://purl.org/dc/terms/"
       }

    If you load a prefix map that is not bijective, it can have unintended consequences. Therefore,
    an error is thrown. You can pass ``strict=False`` if you don't mind having unsafe data. A better data
    structure for situations when there can be CURIE synonyms or even URI prefix synonyms is
    the *extended prefix map* (see below).

Loading Extended Prefix Maps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Extended prefix maps (EPMs) address the issues with prefix maps by including explicit
fields for CURIE prefix synonyms and URI prefix synonyms while maintaining an explicit
field for the preferred CURIE prefix and URI prefix. An abbreviated example (just
containing an entry for ChEBI) looks like:

.. code-block:: json

   [
       {
           "prefix": "CHEBI",
           "uri_prefix": "http://purl.obolibrary.org/obo/CHEBI_",
           "prefix_synonyms": ["chebi"],
           "uri_prefix_synonyms": [
               "https://identifiers.org/chebi:"
           ]
       }
   ]

Extended prefix maps can be loaded with :func:`curies.load_extended_prefix_map`. First,
a prefix map can be loaded directly from a Python data structure like in

.. code-block:: python

    import curies

    epm = [
        {
            "prefix": "CHEBI",
            "uri_prefix": "http://purl.obolibrary.org/obo/CHEBI_",
            "prefix_synonyms": ["chebi"],
            "uri_prefix_synonyms": [
                "https://identifiers.org/chebi:"
            ]
        }
    ]
    converter = curies.load_extended_prefix_map(data)

An extended prefix map can be loaded from a remote file via HTTP, HTTPS, or FTP with

.. code-block:: python

    import curies

    url = "https://raw.githubusercontent.com/mapping-commons/sssom-py/master/src/sssom/obo.epm.json"
    converter = curies.load_extended_prefix_map(url)

Similarly, an extended prefix map stored in a local file can be loaded with the following.
This works with both :class:`pathlib.Path` and vanilla strings.

.. code-block:: python

    from pathlib import Path
    from urllib.request import urlretrieve

    import curies

    url = "https://raw.githubusercontent.com/mapping-commons/sssom-py/master/src/sssom/obo.epm.json"
    path = Path.home().joinpath("Downloads", "obo.epm.json")
    urlretrieve(url, path)
    converter = curies.load_extended_prefix_map(path)

Loading JSON-LD Contexts
~~~~~~~~~~~~~~~~~~~~~~~~
A `JSON-LD context <https://niem.github.io/json/reference/json-ld/context/>`_
allows for embedding of a simple prefix map within a linked data document.
They can be identified hiding in all sorts of JSON (or JSON-like) content
with the key ``@context``. JSON-LD contexts can be loaded using :meth:`curies.Converter.from_jsonld`.

First, a JSON-LD context can be loaded directly from a Python data structure like in

.. code-block:: python

    import curies

    data = {
        "@context": {
            "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_"
        }
    }
    converter = curies.load_jsonld_context(data)

.. note::

    This correctly handles the more complex data structures including ``@prefix`` noted in
    `here <https://github.com/OBOFoundry/OBOFoundry.github.io/issues/2410>`_.

A JSON-LD context can be loaded from a remote file via HTTP, HTTPS, or FTP with

.. code-block:: python

    import curies

    url = "https://raw.githubusercontent.com/biopragmatics/bioregistry/main/exports/contexts/semweb.context.jsonld"
    converter = curies.load_jsonld_context(url)

A JSON-LD context stored in a local file can be loaded with the following.
This works with both :class:`pathlib.Path` and vanilla strings.

.. code-block:: python

    from pathlib import Path
    from urllib.request import urlretrieve

    import curies

    url = "https://raw.githubusercontent.com/biopragmatics/bioregistry/main/exports/contexts/semweb.context.jsonld"
    path = Path.home().joinpath("Downloads", "semweb.context.jsonld")
    urlretrieve(url, path)
    converter = curies.load_jsonld_context(path)

Modifying a Context
-------------------
Incremental Converters
~~~~~~~~~~~~~~~~~~~~~~
As suggested in `#13 <https://github.com/cthoyt/curies/issues/33>`_, new data
can be added to an existing converter with either
:meth:`curies.Converter.add_prefix` or :meth:`curies.Converter.add_record`.
For example, a CURIE and URI prefix for HGNC can be added to the OBO Foundry
converter with the following:

.. code-block::

    import curies

    converter = curies.get_obo_converter()
    converter.add_prefix("hgnc", "https://bioregistry.io/hgnc:")

Similarly, an empty converter can be instantiated using an empty list
for the `records` argument and prefixes can be added one at a time
(note this currently does not allow for adding synonyms separately):

.. code-block::

    import curies

    converter = curies.Converter(records=[])
    converter.add_prefix("hgnc", "https://bioregistry.io/hgnc:")

A more flexible version of this operation first involves constructing
a :class:`curies.Record` object:

.. code-block::

    import curies

    converter = curies.get_obo_converter()
    record = curies.Record(prefix="hgnc", uri_prefix="https://bioregistry.io/hgnc:")
    converter.add_record(record)

By default, both of these operations will fail if the new content conflicts with existing content.
If desired, the ``merge`` argument can be set to true to enable merging. Further, checking
for conflicts and merging can be made to be case insensitive by setting ``case_sensitive`` to false.

Such a merging strategy is the basis for wholesale merging of converters, described below.

Chaining and Merging
~~~~~~~~~~~~~~~~~~~~
This package implements a faultless chain operation :func:`curies.chain` that is configurable for case
sensitivity and fully considers all synonyms.

:func:`curies.chain` prioritizes based on the order given. Therefore, if two prefix maps
having the same prefix but different URI prefixes are given, the first is retained. The second
is retained as a synonym

.. code-block:: python

    import curies

    c1 = curies.load_prefix_map({"GO": "http://purl.obolibrary.org/obo/GO_"})
    c2 = curies.load_prefix_map({"GO": "https://identifiers.org/go:"})
    converter = curies.chain([c1, c2])

    >>> converter.expand("GO:1234567")
    'http://purl.obolibrary.org/obo/GO_1234567'
    >>> converter.compress("http://purl.obolibrary.org/obo/GO_1234567")
    'GO:1234567'
    >>> converter.compress("https://identifiers.org/go:1234567")
    'GO:1234567'

Chain is the perfect tool if you want to override parts of an existing extended
prefix map. For example, if you want to use most of the Bioregistry, but you
would like to specify a custom URI prefix (e.g., using Identifiers.org), you
can do the following

.. code-block:: python

    import curies

    overrides = curies.load_prefix_map({"pubmed": "https://identifiers.org/pubmed:"})
    bioregistry_converter = curies.get_bioregistry_converter()
    converter = curies.chain([overrides, bioregistry_converter])

    >>> converter.expand("pubmed:1234")
    'https://identifiers.org/pubmed:1234'

Subsetting
~~~~~~~~~~
A subset of a converter can be extracted using :meth:`curies.Converter.get_subconverter`.
This functionality is useful for downstream applications like the following:

1. You load a comprehensive extended prefix map, e.g., from the Bioregistry using
   :func:`curies.get_bioregistry_converter()`.
2. You load some data that conforms to this prefix map by convention. This
   is often the case for semantic mappings stored in the
   `SSSOM format <https://github.com/mapping-commons/sssom>`_.
3. You extract the list of prefixes *actually* used within your data
4. You subset the detailed extended prefix map to only include prefixes
   relevant for your data
5. You make some kind of output of the subsetted extended prefix map to
   go with your data. Effectively, this is a way of reconciling data. This
   is especially effective when using the Bioregistry or other comprehensive
   extended prefix maps.

Here's a concrete example of doing this (which also includes a bit of data science)
to do this on the SSSOM mappings from the `Disease Ontology <https://disease-ontology.org/>`_
project.

>>> import curies
>>> import pandas as pd
>>> import itertools as itt
>>> commit = "faca4fc335f9a61902b9c47a1facd52a0d3d2f8b"
>>> url = f"https://raw.githubusercontent.com/mapping-commons/disease-mappings/{commit}/mappings/doid.sssom.tsv"
>>> df = pd.read_csv(url, sep="\t", comment='#')
>>> prefixes = {
...     curies.Reference.from_curie(curie).prefix
...     for column in ["subject_id", "predicate_id", "object_id"]
...     for curie in df[column]
... }
>>> converter = curies.get_bioregistry_converter()
>>> slim_converter = converter.get_subconverter(prefixes)

Faultless handling of overlapping URI prefixes
----------------------------------------------
Most implementations of URI parsing iterate through the CURIE prefix/URI prefix pairs
in a prefix map, check if the given URI starts with the URI prefix, then returns the
CURIE prefix if does. This becomes an issue when a given URI can match multiple
overlapping URI prefixes in the prefix map. For example, the ChEBI URI prefix is
``http://purl.obolibrary.org/obo/CHEBI_`` and the more generic OBO URI prefix
is ``http://purl.obolibrary.org/obo/``. Therefore, it is possible that a URI could be
compressed two different ways, depending on the order of iteration.

:mod:`curies` addresses this by using the `trie <https://en.wikipedia.org/wiki/Trie>`_
data structure, which indexes potentially overlapping strings and allows for efficient
lookup of the longest matching string (e.g., the URI prefix) in the tree to a given target string
(e.g., the URI).

.. image:: img/trie.png
   :width: 200px
   :alt: A graphical depiction of a trie. Reused under the CC0 license from Wikipedia.

This has two benefits. First, it is correct. Second, searching the trie data structure can be done
in sublinear time while iterating over a prefix map can only be done in linear time. When processing
a lot of data, this makes a meaningful difference!

The following code demonstrates that the scenario above. It will always return the correct
CURIE ``CHEBI:1`` instead of the incorrect CURIE ``OBO:CHEBI_1``, regardless of the order of
the dictionary, iteration, or any other factors.

.. code-block::

    import curies

    converter = curies.load_prefix_map({
        "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
        "OBO": "http://purl.obolibrary.org/obo/
    })

    >>> converter.compress("http://purl.obolibrary.org/obo/CHEBI_1")
    'CHEBI:1'

Standardization
---------------
The :class:`curies.Converter` data structure supports prefix and URI prefix synonyms.
The following example demonstrates
using these synonyms to support standardizing prefixes, CURIEs, and URIs. Note below,
the colloquial prefix `gomf`, sometimes used to represent the subspace in the
`Gene Ontology (GO) <https://obofoundry.org/ontology/go>`_ corresponding to molecular
functions, is upgraded to the preferred prefix, ``GO``.

.. code-block::

    from curies import Converter, Record

    converter = Converter([
        Record(
            prefix="GO",
            prefix_synonyms=["gomf", "gocc", "gobp", "go", ...],
            uri_prefix="http://purl.obolibrary.org/obo/GO_",
            uri_prefix_synonyms=[
                "http://amigo.geneontology.org/amigo/term/GO:",
                "https://identifiers.org/GO:",
                ...
            ],
        ),
        # And so on
        ...
    ])

    >>> converter.standardize_prefix("gomf")
    'GO'
    >>> converter.standardize_curie('gomf:0032571')
    'GO:0032571'
    >>> converter.standardize_uri('http://amigo.geneontology.org/amigo/term/GO:0032571')
    'http://purl.obolibrary.org/obo/GO_0032571'

Note: non-standard URIs can still be parsed with :meth:`curies.Converter.parse_uri` and compressed
into CURIEs with :meth:`curies.Converter.compress`.

Bulk Operations
---------------
Apply in bulk to a :class:`pandas.DataFrame` with :meth:`curies.Converter.pd_expand` and
:meth:`curies.Converter.pd_compress`:

.. code-block:: python

    import curies
    import pandas as pd

    df = pd.read_csv(...)
    converter = curies.get_obo_converter()
    converter.pd_compress(df, column=0)
    converter.pd_expand(df, column=0)

    # standardization operations
    converter.pd_standardize_prefix(df, column=0)
    converter.pd_standardize_curie(df, column=0)
    converter.pd_standardize_uri(df, column=0)

Apply in bulk to a CSV file with :meth:`curies.Converter.file_expand` and
:meth:`curies.Converter.file_compress` (defaults to using tab separator):

.. code-block:: python

    import curies

    path = ...
    converter = curies.get_obo_converter()
    # modifies file in place
    converter.file_compress(path, column=0)
    # modifies file in place
    converter.file_expand(path, column=0)

Tools for Developers and Semantic Engineers
-------------------------------------------
Reusable data structures for references
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
While URIs and CURIEs are often represented as strings, for many programmatic applications,
it is preferrable to pre-parse them into a pair of prefix corresponding to a semantic space
and local unique identifier from that semantic space. ``curies`` provides two complementary
data structures for representing these pairs:

1. :mod:`curies.ReferenceTuple` - a native Python :class:`typing.NamedTuple` that is
   storage efficient, can be hashed, can be accessed by slicing, unpacking, or via attributes.
2. :mod:`curies.Reference` - a :class:`pydantic.BaseModel` that can be used directly
   with other Pydantic models, FastAPI, SQLModel, and other JSON-schemata

Internally, :mod:`curies.ReferenceTuple` is used, but there is a big benefit to standardizing
this data type and providing utilities to flip-flop back and forth to :mod:`curies.Reference`,
which is preferable in data validation (such as when parsing OBO ontologies)

Integrating with :mod:`rdflib`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
RDFlib is a pure Python package for manipulating RDF data. The following example shows how to bind the
extended prefix map from a :class:`curies.Converter` to a graph (:class:`rdflib.Graph`).

.. code-block::

    import curies, rdflib, rdflib.namespace

    converter = curies.get_obo_converter()
    graph = rdflib.Graph()

    for prefix, uri_prefix in converter.prefix_map.items():
        graph.bind(prefix, rdflib.Namespace(uri_prefix))

A more flexible approach is to instantiate a namespace manager (:class:`rdflib.namespace.NamespaceManager`)
and bind directly to that.

.. code-block::

    import curies, rdflib

    converter = curies.get_obo_converter()
    namespace_manager = rdflib.namespace.NamespaceManager(rdflib.Graph())

    for prefix, uri_prefix in converter.prefix_map.items():
        namespace_manager.bind(prefix, rdflib.Namespace(uri_prefix))

URI references for use in RDFLib's graph class can be constructed from
CURIEs using a combination of :meth:`curies.Converter.expand` and :class:`rdflib.URIRef`.

.. code-block::

    import curies, rdflib

    converter = curies.get_obo_converter()

    uri_ref = rdflib.URIRef(converter.expand("CHEBI:138488"))
