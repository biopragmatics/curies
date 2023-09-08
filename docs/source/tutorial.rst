Getting Started
===============
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
