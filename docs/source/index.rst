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
