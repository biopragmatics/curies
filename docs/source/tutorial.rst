Getting Started
===============
Loading a Context
-----------------
Loading a pre-defined context
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Several converters can be instantiated from pre-defined web-based resources:

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

Loading Extended Prefix Maps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Loading JSON-LD Contexts
~~~~~~~~~~~~~~~~~~~~~~~~
All loader function work on local file paths, remote URLs, and pre-loaded
data structures. For example, a converter can be instantiated from a web-based
resource in JSON-LD format:

.. code-block:: python

    from curies import Converter

    url = "https://raw.githubusercontent.com/biopragmatics/bioregistry/main/exports/contexts/semweb.context.jsonld"
    converter = Converter.from_jsonld(url)

Local file path (this works with :class:`pathlib.Path` or vanilla strings)

.. code-block:: python

    from urllib.request import urlretrieve
    from curies import Converter
    from pathlib import Path

    url = "https://raw.githubusercontent.com/biopragmatics/bioregistry/main/exports/contexts/semweb.context.jsonld"
    path = Path.home().joinpath("Downloads", "semweb.context.jsonld")
    urlretrieve(url, path)
    converter = Converter.from_jsonld(path)

Directly from a data structure

.. code-block:: python

    from curies import Converter

    data = {
        "@context": {
            "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_"
        }
    }
    converter = Converter.from_jsonld(data)

.. note::

    This correctly handles the more complex data structures including ``@prefix`` noted in
    `here <https://github.com/OBOFoundry/OBOFoundry.github.io/issues/2410>`_.

Incremental Converters
----------------------
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
--------------------
This package implements a faultless chain operation :func:`curies.chain` that is configurable for case
sensitivity and fully considers all synonyms.

:func:`curies.chain` prioritizes based on the order given. Therefore, if two prefix maps
having the same prefix but different URI prefixes are given, the first is retained. The second
is retained as a synonym

.. code-block:: python

    import curies

    c1 = curies.read_prefix_map({"GO": "http://purl.obolibrary.org/obo/GO_"})
    c2 = curies.read_prefix_map({"GO": "https://identifiers.org/go:"})
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

    overrides = curies.read_prefix_map({"pubmed": "https://identifiers.org/pubmed:"})
    bioregistry_converter = curies.get_bioregistry_converter()
    converter = curies.chain([overrides, bioregistry_converter])

    >>> converter.expand("pubmed:1234")
    'https://identifiers.org/pubmed:1234'

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

    converter = curies.read_prefix_map({
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

Reusable data structures for references
---------------------------------------
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
------------------------------
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
