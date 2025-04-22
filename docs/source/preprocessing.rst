Converter with Preprocessing
============================

When simple expansion and contraction aren't enough, and you want to inject global or
context-specific rewrite rules, you can wrap a :class:`curies.Converter` and
preprocessing rules encoded in an instance of :class:`curies.PreprocessingRules` inside
a :class:`curies.PreprocessingConverter`.

For example, you always want to fix legacy references to the ``OBO_REL`` namespace:

.. code-block:: python

    import curies
    from curies import PreprocessingRules, PreprocessingConverter, PreprocessingRewrites

    rules = PreprocessingRules(
        rewrites=PreprocessingRewrites(
            full={"OBO_REL:is_a": "rdfs:subClassOf"}
        )
    )

    converter = curies.get_obo_converter()
    converter = PreprocessingConverter.from_converter(
        converter, rules=rules
    )

    >>> converter.parse_curie("OBO_REL:is_a")
    ReferenceTuple('rdfs', 'subClassOf')

Similarly, there may be a whole class of references that need to be fixed
based on their prefix, such as the ``APOLLO:SV_`` references that are mangled
by the OWLAPI due to the OBO Foundry's PURL rules

.. code-block:: python

    import curies
    from curies import PreprocessingRules, PreprocessingConverter, PreprocessingRewrites

    rules = PreprocessingRules(
        rewrites=PreprocessingRewrites(
            prefix={"APOLLO:SV_": "APOLLO_SV:"}
        )
    )

    converter = curies.get_obo_converter()
    converter = PreprocessingConverter.from_converter(
        converter, rules=rules
    )

    >>> converter.parse_curie("APOLLO:SV_1234567")
    ReferenceTuple('APOLLO_SV', '1234567')

Some rewrite rules only apply to a specific resource, because of its own quirks
in curation or encoding. For example, CHMO encodes OrangeBook entries with ``orange``
as a prefix, which is not typically specific enough to