curies |release| Documentation
==============================

Uniform resource identifiers (URIs) and compact URIs (CURIEs) have become the
predominant syntaxes for identifying concepts in linked data applications. Therefore,
efficient, faultless, and idiomatic conversion between them is a crucial low-level
utility whose need is ubiquitous across many codebases.

:mod:`curies` fills this need. This Python package can be used by a variety of people:

1. **Data Scientist** - someone who consumes and modifies data to suit an analysis or
   application. For example, they might want to convert tabular data containing CURIEs
   into IRIs, translate into RDF, then query with SPARQL.
2. **Curator** - someone who creates data. For example, an ontologist may want to curate
   using CURIEs but have their toolchain 1) validate the syntax and semantics and 2)
   convert to IRIs for their data persistence
3. **Data Consumer** - someone who consumes data. This kind of user likely won't
   interact with :mod:`curies` directly, but will likely use tools that build on top of
   it. For example, someone using the Bioregistry resolution service uses this package's
   expansion utilities indirectly.
4. **Software Developer** - someone who develops tools to support data creators, data
   consumers, and other software developers. For example, a software developer might
   want to make their toolchain more generic for loading, merging, and outputting prefix
   maps and extended prefix maps.

For many users, expansion (CURIE to URI) and contraction (URI to CURIE) are the two most
important tools.

.. code-block:: python

    import curies

    # Get a converter
    converter = curies.get_obo_converter()

    assert converter.compress("http://purl.obolibrary.org/obo/CHEBI_1") == "CHEBI:1"

    assert converter.expand("CHEBI:1") == "http://purl.obolibrary.org/obo/CHEBI_1"

See the tutorial for more pre-defined converters, information on defining custom
converters, chaining converters, and more.

Installation
------------

The most recent release can be installed from `PyPI <https://pypi.org/project/curies>`_
with:

.. code-block:: shell

    $ pip install curies

The most recent code and data can be installed directly from GitHub with:

.. code-block:: shell

    $ pip install git+https://github.com/cthoyt/curies.git

.. toctree::
    :maxdepth: 2
    :caption: Contents:

    tutorial
    reconciliation
    discovery
    struct
    api
    services/index
    typing
    w3c
