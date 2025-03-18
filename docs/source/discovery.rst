URI Prefix Discovery
====================

.. automodule:: curies.discovery

Discovering URI Prefixes from an Ontology
-----------------------------------------

A common place where discovering URI prefixes is important is when working with new
ontologies. In the following example, we look at the `Academic Event Ontology (AEON)
<https://bioregistry.io/aeon>`_. This is an ontology developed under OBO Foundry
principles describing academic events. Accordingly, it includes many URI references to
terms in OBO Foundry ontologies.

In this tutorial, we use :func:`curies.discover` (and then
:func:`curies.discover_from_rdf` as a nice convenience function) to load the ontology in
the RDF/XML format and discover putative URI prefixes.

.. code-block:: python

    import curies
    from curies.discovery import get_uris_from_rdf

    ONTOLOGY_URL = "https://raw.githubusercontent.com/tibonto/aeon/main/aeon.owl"

    uris = get_uris_from_rdf(ONTOLOGY_URL, format="xml")
    discovered_converter = curies.discover(uris)
    # note, these two steps can be combine with curies.discover_from_rdf,
    # and we'll do that in the following examples

We discovered the fifty URI prefixes in the following table. Many of them appear to be
OBO Foundry URI prefixes or semantic web prefixes, so in the next step, we'll use prior
knowledge to reduce the false discovery rate.

============ ==============================================================================
curie_prefix uri_prefix
============ ==============================================================================
ns1          ``http://ontologydesignpatterns.org/wiki/Community:Parts_and_``
ns2          ``http://protege.stanford.edu/plugins/owl/protege#``
ns3          ``http://purl.obolibrary.org/obo/AEON_``
ns4          ``http://purl.obolibrary.org/obo/APOLLO_SV_``
ns5          ``http://purl.obolibrary.org/obo/BFO_``
ns6          ``http://purl.obolibrary.org/obo/CRO_``
ns7          ``http://purl.obolibrary.org/obo/ENVO_``
ns8          ``http://purl.obolibrary.org/obo/IAO_``
ns9          ``http://purl.obolibrary.org/obo/ICO_``
ns10         ``http://purl.obolibrary.org/obo/NCBITaxon_``
ns11         ``http://purl.obolibrary.org/obo/OBIB_``
ns12         ``http://purl.obolibrary.org/obo/OBI_``
ns13         ``http://purl.obolibrary.org/obo/OMO_``
ns14         ``http://purl.obolibrary.org/obo/OOSTT_``
ns15         ``http://purl.obolibrary.org/obo/RO_``
ns16         ``http://purl.obolibrary.org/obo/TXPO_``
ns17         ``http://purl.obolibrary.org/obo/bfo/axiom/``
ns18         ``http://purl.obolibrary.org/obo/valid_for_``
ns19         ``http://purl.obolibrary.org/obo/valid_for_go_``
ns20         ``http://purl.obolibrary.org/obo/valid_for_go_annotation_``
ns21         ``http://purl.obolibrary.org/obo/wikiCFP_``
ns22         ``http://purl.org/dc/elements/1.1/``
ns23         ``http://purl.org/dc/terms/``
ns24         ``http://usefulinc.com/ns/doap#``
ns25         ``http://wiki.geneontology.org/index.php/Involved_``
ns26         ``http://www.geneontology.org/formats/oboInOwl#``
ns27         ``http://www.geneontology.org/formats/oboInOwl#created_``
ns28         ``http://www.w3.org/1999/02/22-rdf-syntax-ns#``
ns29         ``http://www.w3.org/2000/01/rdf-schema#``
ns30         ``http://www.w3.org/2001/XMLSchema#``
ns31         ``http://www.w3.org/2002/07/owl#``
ns32         ``http://www.w3.org/2003/11/swrl#``
ns33         ``http://www.w3.org/2004/02/skos/core#``
ns34         ``http://www.w3.org/ns/prov#``
ns35         ``http://xmlns.com/foaf/0.1/``
ns36         ``https://en.wikipedia.org/wiki/Allen%27s_interval_``
ns37         ``https://groups.google.com/d/msg/bfo-owl-devel/s9Uug5QmAws/ZDRnpiIi_``
ns38         ``https://ror.org/``
ns39         ``https://w3id.org/scholarlydata/ontology/conference-ontology.owl#``
ns40         ``https://w3id.org/seo#``
ns41         ``https://www.confident-conference.org/index.php/Academic_Field:Information_``
ns42         ``https://www.confident-conference.org/index.php/Event:VIVO_``
ns43         ``https://www.confident-conference.org/index.php/Event:VIVO_2021_``
ns44         ``https://www.confident-conference.org/index.php/Event:VIVO_2021_orga_``
ns45         ``https://www.confident-conference.org/index.php/Event:VIVO_2021_talk1_``
ns46         ``https://www.confident-conference.org/index.php/Event:VIVO_2021_talk2_``
ns47         ``https://www.confident-conference.org/index.php/Event_Series:VIVO_``
ns48         ``https://www.wikidata.org/wiki/``
ns49         ``https://www.wikidata.org/wiki/Wikidata:Property_proposal/colocated_``
ns50         ``urn:swrl#``
============ ==============================================================================

In the following block, we chain together (extended) prefix maps from the OBO Foundry as
well as a "semantic web" prefix map to try and reduce the number of false positives by
passing them through the ``converter`` keyword argument.

.. code-block:: python

    import curies

    ONTOLOGY_URL = "https://raw.githubusercontent.com/tibonto/aeon/main/aeon.owl"
    SEMWEB_URL = "https://raw.githubusercontent.com/biopragmatics/bioregistry/main/exports/contexts/semweb.context.jsonld"

    base_converter = curies.chain(
        [
            curies.load_jsonld_context(SEMWEB_URL),
            curies.get_obo_converter(),
        ]
    )

    discovered_converter = curies.discover_from_rdf(
        ONTOLOGY_URL, format="xml", converter=base_converter
    )

We reduced the number of putative URI prefixes in half in the following table. However,
we can still identify some putative URI prefixes that likely would have appeared in a
more comprehensive (extended) prefix map such as the Bioregistry such as:

- ``https://ror.org/`` for the `Research Organization Registry (ROR)
  <https://bioregistry.io/ror>`_
- ``https://w3id.org/seo#`` for the `Scientific Event Ontology (SEO)
  <https://bioregistry.io/seo>`_
- ``http://usefulinc.com/ns/doap#`` for the `Description of a Project (DOAP) vocabulary
  <https://bioregistry.io/doap>`_

Despite this, we're on our way! It's also obvious that several of the remaining putative
URI prefixes come from non-standard usage of the OBO PURL system (e.g.,
``http://purl.obolibrary.org/obo/valid_for_go_annotation_``) and some are proper false
positives due to using ``_`` as a delimiter (e.g.,
``https://www.confident-conference.org/index.php/Event:VIVO_2021_talk2_``).

============ ==============================================================================
curie_prefix uri_prefix
============ ==============================================================================
ns1          ``http://ontologydesignpatterns.org/wiki/Community:Parts_and_``
ns2          ``http://protege.stanford.edu/plugins/owl/protege#``
ns3          ``http://purl.obolibrary.org/obo/AEON_``
ns4          ``http://purl.obolibrary.org/obo/bfo/axiom/``
ns5          ``http://purl.obolibrary.org/obo/valid_for_``
ns6          ``http://purl.obolibrary.org/obo/valid_for_go_``
ns7          ``http://purl.obolibrary.org/obo/valid_for_go_annotation_``
ns8          ``http://purl.obolibrary.org/obo/wikiCFP_``
ns9          ``http://usefulinc.com/ns/doap#``
ns10         ``http://wiki.geneontology.org/index.php/Involved_``
ns11         ``https://en.wikipedia.org/wiki/Allen%27s_interval_``
ns12         ``https://groups.google.com/d/msg/bfo-owl-devel/s9Uug5QmAws/ZDRnpiIi_``
ns13         ``https://ror.org/``
ns14         ``https://w3id.org/scholarlydata/ontology/conference-ontology.owl#``
ns15         ``https://w3id.org/seo#``
ns16         ``https://www.confident-conference.org/index.php/Academic_Field:Information_``
ns17         ``https://www.confident-conference.org/index.php/Event:VIVO_``
ns18         ``https://www.confident-conference.org/index.php/Event:VIVO_2021_``
ns19         ``https://www.confident-conference.org/index.php/Event:VIVO_2021_orga_``
ns20         ``https://www.confident-conference.org/index.php/Event:VIVO_2021_talk1_``
ns21         ``https://www.confident-conference.org/index.php/Event:VIVO_2021_talk2_``
ns22         ``https://www.confident-conference.org/index.php/Event_Series:VIVO_``
ns23         ``https://www.wikidata.org/wiki/``
ns24         ``https://www.wikidata.org/wiki/Wikidata:Property_proposal/colocated_``
ns25         ``urn:swrl#``
============ ==============================================================================

As a final step in our iterative journey of URI prefix discovery, we're going to use a
cutoff for a minimum of two appearances of a URI prefix to reduce the most spurious
false positives.

.. code-block:: python

    import curies

    ONTOLOGY_URL = "https://raw.githubusercontent.com/tibonto/aeon/main/aeon.owl"
    SEMWEB_URL = "https://raw.githubusercontent.com/biopragmatics/bioregistry/main/exports/contexts/semweb.context.jsonld"

    base_converter = curies.chain(
        [
            curies.load_jsonld_context(SEMWEB_URL),
            curies.get_obo_converter(),
        ]
    )

    discovered_converter = curies.discover_from_rdf(
        ONTOLOGY_URL, format="xml", converter=base_converter, cutoff=2
    )

We have reduced the list to a manageable set of 9 putative URI prefixes in the following
table.

============ =========================================================================
curie_prefix uri_prefix
============ =========================================================================
ns1          ``http://purl.obolibrary.org/obo/AEON_``
ns2          ``http://purl.obolibrary.org/obo/bfo/axiom/``
ns3          ``http://purl.obolibrary.org/obo/valid_for_go_``
ns4          ``https://w3id.org/scholarlydata/ontology/conference-ontology.owl#``
ns5          ``https://w3id.org/seo#``
ns6          ``https://www.confident-conference.org/index.php/Event:VIVO_2021_``
ns7          ``https://www.confident-conference.org/index.php/Event:VIVO_2021_talk1_``
ns8          ``https://www.confident-conference.org/index.php/Event:VIVO_2021_talk2_``
ns9          ``urn:swrl#``
============ =========================================================================

Here are the calls to be made:

- ``ns1`` represents the AEON vocabulary itself and should be given the ``aeon`` prefix.
- ``ns2`` and ``ns3``` are all false positives
- ``ns6``, ``ns7``, and ``ns8`` are a tricky case - they have a meaningful overlap that
  can't be easily automatically detected (yet). In this case, it makes the most sense to
  add the shortest one manually to the base converter with some unique name (don't use
  ``ns6`` as it will cause conflicts later), like in:

  .. code-block:: python

      base_converter = curies.chain(
          [
              curies.load_jsonld_context(SEMWEB_URL),
              curies.get_obo_converter(),
              curies.load_prefix_map(
                  {
                      "confident_event_vivo_2021": "https://www.confident-conference.org/index.php/Event:VIVO_2021_"
                  }
              ),
          ]
      )

  In reality, these are all part of the `ConfIDent Event
  <https://bioregistry.io/confident.event>`_ vocabulary, which has the URI prefix
  ``https://www.confident-conference.org/index.php/Event:``.

- ``ns4`` represents the `Conference Ontology <https://bioregistry.io/conference>`_ and
  should be given the ``conference`` prefix.
- ``ns5`` represents the `Scientific Event Ontology (SEO) <https://bioregistry.io/seo>`_
  and should be given the ``seo`` prefix.
- ``ns9`` represents the `Semantic Web Rule Language
  <https://bioregistry.io/registry/swrl>`_, though using URNs is an interesting choice
  in serialization.

After we've made these calls, it's a good idea to write an (extended) prefix map. In
this case, since we aren't working with CURIE prefix synonyms nor URI prefix synonyms,
it's okay to write a simple prefix map or a JSON-LD context without losing information.

.. note::

        Postscript: throughout this guide, we used the following Python code to create
        the RST tables:

    .. code-block:: python

        def print_converter(converter) -> None:
            from tabulate import tabulate

            rows = sorted(
                [
                    (record.prefix, f"``{record.uri_prefix}``")
                    for record in discovered_converter.records
                ],
                key=lambda t: int(t[0].removeprefix("ns")),
            )
            print(tabulate(rows, headers=["curie_prefix", "uri_prefix"], tablefmt="rst"))

Just Make It Work, or, A Guide to Being a Questionable Semantic Citizen
-----------------------------------------------------------------------

The goal of the :mod:`curies` package is to provide the tools towards making
semantically well-defined data, which has a meaningful (extended) prefix map associated
with it. Maybe you're in an organization that doesn't really care about the utility of
nice prefix maps, and just wants to get the job done where you need to turn URIs into
_some_ CURIEs.

Here's a recipe for doing this, based on the last example with AEON:

.. code-block:: python

    import curies

    ONTOLOGY_URL = "https://raw.githubusercontent.com/tibonto/aeon/main/aeon.owl"

    # Use the Bioregistry as a base prefix since it's the most comprehensive one
    base_converter = curies.get_bioregistry_converter()

    # Only discover what the Bioregistry doesn't already have
    discovered_converter = curies.discover_from_rdf(
        ONTOLOGY_URL, format="xml", converter=base_converter
    )

    # Chain together the base converter with the discoveries
    augmented_converter = curies.chain([base_converter, discovered_converter])

With the augmented converter, you can now convert all URIs in the ontology into CURIEs.
They will have a smattering of unintelligible prefixes with no meaning, but at least the
job is done!
