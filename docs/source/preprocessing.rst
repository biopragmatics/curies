Converter with Preprocessing
============================

When simple expansion and contraction aren't enough, and you want to inject global or
context-specific rewrite rules, you can wrap a :class:`curies.Converter` and
preprocessing rules encoded in an instance of :class:`curies.PreprocessingRules` inside
a :class:`curies.PreprocessingConverter`.

Rewrites
--------

For example, you always want to fix legacy references to the ``OBO_REL`` namespace:

.. code-block:: python

    import curies
    from curies import PreprocessingRules, PreprocessingConverter, PreprocessingRewrites

    rules = PreprocessingRules(
        rewrites=PreprocessingRewrites(
            full={"OBO_REL:is_a": "rdfs:subClassOf"},
        ),
    )

    converter = curies.get_obo_converter()
    converter = PreprocessingConverter.from_converter(
        converter, rules=rules,
    )

    >>> converter.parse_curie("OBO_REL:is_a")
    ReferenceTuple('rdfs', 'subClassOf')

Similarly, there may be a whole class of references that need to be fixed based on their
prefix, such as the ``APOLLO:SV_`` references that are mangled by the OWLAPI due to the
OBO Foundry's PURL rules

.. code-block:: python

    import curies
    from curies import PreprocessingRules, PreprocessingConverter, PreprocessingRewrites

    rules = PreprocessingRules(
        rewrites=PreprocessingRewrites(
            prefix={"APOLLO:SV_": "APOLLO_SV:"},
        )
    )

    converter = curies.get_obo_converter()
    converter = PreprocessingConverter.from_converter(
        converter, rules=rules,
    )

    >>> converter.parse_curie("APOLLO:SV_1234567")
    ReferenceTuple('APOLLO_SV', '1234567')

The CURIE and URI rewrites are unified. Therefore, you can also use a URI as a rewrite,
such as handling Creative Commons license URLs, which unfortunately aren't themselves
part of a semantic space for licenses. Luckily, SPDX is, and we can remap to that.

.. code-block:: python

    import curies
    from curies import PreprocessingRules, PreprocessingConverter, PreprocessingRewrites

    rules = PreprocessingRules(
        rewrites=PreprocessingRewrites(
            full={"http://creativecommons.org/licenses/by/3.0/": "spdx:CC-BY-3.0",},
        )
    )

    converter = curies.get_obo_converter()
    converter.add_prefix("spdx", "https://spdx.org/licenses/")
    converter = PreprocessingConverter.from_converter(
        converter, rules=rules,
    )

    >>> converter.parse_uri("http://creativecommons.org/licenses/by/3.0/")
    ReferenceTuple('spdx', 'CC-BY-3.0')

Some rewrite rules only apply to a specific resource, because of its own quirks in
curation or encoding. For example, CHMO encodes OrangeBook entries with ``orange`` as a
prefix, which is not typically specific enough to warrant curating ``orange`` as a
prefix, e.g., in the Bioregistry

.. code-block:: python

    import curies
    from curies import PreprocessingRules, PreprocessingConverter, PreprocessingRewrites

    rules = PreprocessingRules(
        rewrites=PreprocessingRewrites(
            resource_prefix={
                "CHMO": {"orange:": "orangebook:"},
            },
        ),
    )

    converter = curies.get_obo_converter()
    converter.add_prefix("orangebook", "https://bioregistry.io/orangebook:")
    converter = PreprocessingConverter.from_converter(
        converter, rules=rules,
    )

    >>> converter.parse_curie("orange:10.2.1.1.3")
    ReferenceTuple('orangebook', '10.2.1.1.3')

Similarly, this can be used to inject knowledge about resources that improperly import
EDAM sub-trees such as MCRO, which uses ``format`` as a prefix where it means
``edam.format``

Blocks
------

Some references are _never_ informative, and can be configured to be thrown away, such
as ``Bgee:curators``, ``BioGRID:curators``, ``GROUP:OBI``, and similar group curation
flags.

.. code-block:: python

    import curies
    from curies import PreprocessingRules, PreprocessingConverter, PreprocessingBlocklists

    rules = PreprocessingRules(
        blocklists=PreprocessingBlocklists(
            full=["Bgee:curators", "BioGRID:curators", "GROUP:OBI"],
        ),
    )

    converter = curies.get_obo_converter()
    converter = PreprocessingConverter.from_converter(
        converter, rules=rules,
    )

    # raises a BlocklistError
    >>> converter.parse_curie("GROUP:OBI")

Blocklists cause throwing an exception that can be handled by downstream code, such as
returning a None. This is done because in some places, it's nice to have the distinction
between ``None`` being returned by parsing failing, versus actively being blocked. This
can be toggled with the ``block_action`` argument.
