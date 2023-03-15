curies |release| Documentation
==============================
Installation
------------
The most recent release can be installed from
`PyPI <https://pypi.org/project/curies>`_ with:

.. code-block:: shell

    $ pip install curies

The most recent code and data can be installed directly from GitHub with:

.. code-block:: shell

    $ pip install git+https://github.com/cthoyt/curies.git

.. automodapi:: curies
   :no-inheritance-diagram:

CLI Usage
---------
.. automodule:: curies.cli

Integrating with :mod:`rdflib`
------------------------------
RDFlib is a pure Python package for manipulating RDF data. The following example shows how to bind the
prefix map from a :class:`curies.Converter` to a graph (:class:`rdflib.Graph`).

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

Incremental Converters
----------------------
As suggested in `#13 <https://github.com/cthoyt/curies/issues/33>`_, new prefixes
can be added to an existing converter like in the following:

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

Identifier Mapping Service
--------------------------
.. automodapi:: curies.mapping_service
   :no-inheritance-diagram:
