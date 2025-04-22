Converter with Preprocessing
============================

When simple expansion and contraction aren't enough, and you want to inject global or
context-specific rewrite rules, you can wrap a :class:`curies.Converter` and
preprocessing rules encoded in an instance of :class:`curies.PreprocessingRules` inside
a :class:`curies.PreprocessingConverter`.

For example, you always want to fix legacy references to the ``OBO_REL`` namespace:

.. code-block:: python

    import curies
    from curies import PreprocessingRules, PreprocessingConverter
    from curies.wrapped import Rewrites

    rules = PreprocessingRules(
        rewrites=Rewrites(
            full={"OBO_REL:is_a": "rdfs:subClassOf"}
        )
    )

    converter = curies.get_obo_converter()
    converter = PreprocessingConverter.from_converter(
        converter, rules=rules
    )

    >>> converter.parse_curie("OBO_REL:is_a")
    ReferenceTuple('rdfs', 'subClassOf')
