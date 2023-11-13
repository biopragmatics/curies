URI Prefix Discovery
====================
.. warning::

    This tutorial introduces tools that enable you to be a bad Semantic Citizen!
    Use these tools at your own peril.

Discovering URI Prefixes from an Ontology
-----------------------------------------
A common place where discovering URI prefixes is important is when working with new ontologies.
Here, we use :func:`curies.discover_from_rdf` to load an ontology in the RDF/XML format.

.. code-block:: python

    import curies
    from tabulate import tabulate

    ONTOLOGY_URL = "https://raw.githubusercontent.com/tibonto/aeon/main/aeon.owl"
    SEMWEB_URL = "https://raw.githubusercontent.com/biopragmatics/bioregistry/main/exports/contexts/semweb.context.jsonld"

    # Load up some pre-registered context
    converter = curies.chain([
        curies.load_jsonld_context(SEMWEB_URL),
        curies.get_obo_converter(),
    ])

    discovered_converter = curies.discover_from_rdf(
        converter,
        graph=ONTOLOGY_URL,
        graph_format="xml",
        delimiters="#/_",
        cutoff=5,
    )

    rows = [(record.prefix, f"``{record.uri_prefix}``") for record in discovered_converter.records]
    print(tabulate(rows, headers=["curie_prefix", "uri_prefix"], tablefmt="rst"))

Results in:

==============  ====================================================================
curie_prefix    uri_prefix
==============  ====================================================================
ns1             ``http://purl.obolibrary.org/obo/AEON_``
ns2             ``http://purl.obolibrary.org/obo/bfo/axiom/``
ns3             ``https://github.com/tibonto/aeon/issues/``
ns4             ``https://w3id.org/scholarlydata/ontology/conference-ontology.owl#``
ns5             ``https://w3id.org/seo#``
ns6             ``https://www.confident-conference.org/index.php/Event:VIVO_2021_``
==============  ====================================================================

.. note::

    An alternative to discovering new prefixes is often to supplement your project-specific (extended)
    prefix map with a comprehensive one, such as The Bioregistry.
