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
        ONTOLOGY_URL,
        format="xml",
        converter=converter,
    )

    rows = [(record.prefix, f"``{record.uri_prefix}``") for record in discovered_converter.records]
    print(tabulate(rows, headers=["curie_prefix", "uri_prefix"], tablefmt="rst"))

Results in:

==============  ==============================================================================
curie_prefix    uri_prefix
==============  ==============================================================================
ns1             ``http://ontologydesignpatterns.org/wiki/Community:Parts_and_``
ns10            ``http://wiki.geneontology.org/index.php/Involved_``
ns11            ``https://en.wikipedia.org/wiki/Allen%27s_interval_``
ns12            ``https://groups.google.com/d/msg/bfo-owl-devel/s9Uug5QmAws/ZDRnpiIi_``
ns13            ``https://ror.org/``
ns14            ``https://w3id.org/scholarlydata/ontology/conference-ontology.owl#``
ns15            ``https://w3id.org/seo#``
ns16            ``https://www.confident-conference.org/index.php/Academic_Field:Information_``
ns17            ``https://www.confident-conference.org/index.php/Event:VIVO_``
ns18            ``https://www.confident-conference.org/index.php/Event:VIVO_2021_``
ns19            ``https://www.confident-conference.org/index.php/Event:VIVO_2021_orga_``
ns2             ``http://protege.stanford.edu/plugins/owl/protege#``
ns20            ``https://www.confident-conference.org/index.php/Event:VIVO_2021_talk1_``
ns21            ``https://www.confident-conference.org/index.php/Event:VIVO_2021_talk2_``
ns22            ``https://www.confident-conference.org/index.php/Event_Series:VIVO_``
ns23            ``https://www.wikidata.org/wiki/``
ns24            ``https://www.wikidata.org/wiki/Wikidata:Property_proposal/colocated_``
ns25            ``urn:swrl#``
ns3             ``http://purl.obolibrary.org/obo/AEON_``
ns4             ``http://purl.obolibrary.org/obo/bfo/axiom/``
ns5             ``http://purl.obolibrary.org/obo/valid_for_``
ns6             ``http://purl.obolibrary.org/obo/valid_for_go_``
ns7             ``http://purl.obolibrary.org/obo/valid_for_go_annotation_``
ns8             ``http://purl.obolibrary.org/obo/wikiCFP_``
ns9             ``http://usefulinc.com/ns/doap#``
==============  ==============================================================================

There are several URI prefixes that feel like false positives, so let's set a cutoff of a minimum
of 2 appearances for it to make it.

.. code-block:: python

    discovered_converter = curies.discover_from_rdf(
        ONTOLOGY_URL,
        format="xml",
        cutoff=2,
        converter=converter,
    )

    rows = [(record.prefix, f"``{record.uri_prefix}``") for record in discovered_converter.records]
    print(tabulate(rows, headers=["curie_prefix", "uri_prefix"], tablefmt="rst"))

Now, the list is much shorter and more managable, but there still appear to be false positives.

==============  =========================================================================
curie_prefix    uri_prefix
==============  =========================================================================
ns1             ``http://purl.obolibrary.org/obo/AEON_``
ns2             ``http://purl.obolibrary.org/obo/bfo/axiom/``
ns3             ``http://purl.obolibrary.org/obo/valid_for_go_``
ns4             ``https://w3id.org/scholarlydata/ontology/conference-ontology.owl#``
ns5             ``https://w3id.org/seo#``
ns6             ``https://www.confident-conference.org/index.php/Event:VIVO_2021_``
ns7             ``https://www.confident-conference.org/index.php/Event:VIVO_2021_talk1_``
ns8             ``https://www.confident-conference.org/index.php/Event:VIVO_2021_talk2_``
ns9             ``urn:swrl#``
==============  =========================================================================

.. note::

    An alternative to discovering new prefixes is often to supplement your project-specific (extended)
    prefix map with a comprehensive one, such as The Bioregistry.
