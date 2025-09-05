Working with Dataframes
=======================

Filtering
---------

In the following examples, we'll use a dataframe representing semantic mappings between
disease ontologies in the SSSOM format:

============ =============== =============== ============================
subject_id   predicate_id    object_id       mapping_justification
============ =============== =============== ============================
DOID:0080795 skos:exactMatch EFO:0003029     semapv:ManualMappingCuration
DOID:0080795 skos:exactMatch mesh:D015471    semapv:ManualMappingCuration
DOID:0080799 skos:exactMatch EFO:1000527     semapv:ManualMappingCuration
DOID:0080808 skos:exactMatch mesh:D000069295 semapv:ManualMappingCuration
============ =============== =============== ============================

To get the set of unique prefixes appearing in a column, use
:func:`curies.dataframe.get_df_unique_prefixes`:

.. code-block:: python

    from curies.dataframe import get_df_unique_prefixes

    df = ...
    prefixes = get_df_unique_prefixes(df, column="object_id")
    assert prefixes == {"EFO", "mesh"}

To filter to objects that use EFO, use :func:`curies.dataframe.filter_df_by_prefixes`:

.. code-block:: python

    from curies.dataframe import filter_df_by_prefixes

    df = ...
    df = filter_df_by_prefixes(df, column="object_id", prefixes=["efo"])

============ =============== =========== ============================
subject_id   predicate_id    object_id   mapping_justification
============ =============== =========== ============================
DOID:0080795 skos:exactMatch EFO:0003029 semapv:ManualMappingCuration
DOID:0080799 skos:exactMatch EFO:1000527 semapv:ManualMappingCuration
============ =============== =========== ============================

To filter to rows that have the subject ``DOID:0080795``, use
:func:`curies.dataframe.filter_df_by_curies`:

.. code-block:: python

    from curies.dataframe import filter_df_by_curies

    df = ...
    df = filter_df_by_curies(df, column="subjects_id", curies=["DOID:0080795"])

============ =============== ============ ============================
subject_id   predicate_id    object_id    mapping_justification
============ =============== ============ ============================
DOID:0080795 skos:exactMatch EFO:0003029  semapv:ManualMappingCuration
DOID:0080795 skos:exactMatch mesh:D015471 semapv:ManualMappingCuration
============ =============== ============ ============================
