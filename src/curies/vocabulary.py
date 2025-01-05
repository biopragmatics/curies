"""A module containing pre-defined references."""

from __future__ import annotations

from typing import Literal

from typing_extensions import TypeAlias

from curies import NamedReference as Reference

# Synonyms

## Synonym Relations

#: The parent property for having synonyms, see :data:`synonym_scopes`
#: for a dictionary of all synonym types
has_synonym = Reference(prefix="oboInOwl", identifier="hasSynonym", name="has synonym")

has_exact_synonym = Reference(
    prefix="oboInOwl", identifier="hasExactSynonym", name="has exact synonym"
)
has_narrow_synonym = Reference(
    prefix="oboInOwl", identifier="hasNarrowSynonym", name="has narrow synonym"
)
has_broad_synonym = Reference(
    prefix="oboInOwl", identifier="hasBroadSynonym", name="has broad synonym"
)
has_related_synonym = Reference(
    prefix="oboInOwl", identifier="hasRelatedSynonym", name="has related synonym"
)

#: A list of strings used to refer to synonym types in ``oboInOwl``
SynonymScope: TypeAlias = Literal["EXACT", "NARROW", "BROAD", "RELATED"]

#: A mapping from synonym scopes to references
synonym_scopes: dict[SynonymScope, Reference] = {
    "EXACT": has_exact_synonym,
    "NARROW": has_narrow_synonym,
    "BROAD": has_broad_synonym,
    "RELATED": has_related_synonym,
}

## OMO Synonym Types

#: The parent class for all synonym types, see :data:`synonym_types`
#: for the set of all synonym types
synonym_type = Reference(prefix="oboInOwl", identifier="SynonymType", name="synonym type")

abbreviation = Reference(prefix="OMO", identifier="0003000", name="abbreviation")
ambiguous_synonym = Reference(prefix="OMO", identifier="0003001", name="ambiguous synonym")
dubious_synonym = Reference(prefix="OMO", identifier="0003002", name="dubious synonym")
layperson_synonym = Reference(prefix="OMO", identifier="0003003", name="layperson synonym")
plural_form = Reference(prefix="OMO", identifier="0003004", name="plural form")
uk_spelling = Reference(prefix="OMO", identifier="0003005", name="UK spelling synonym")
misspelling = Reference(prefix="OMO", identifier="0003006", name="misspelling")
misnomer = Reference(prefix="OMO", identifier="0003007", name="misnomer")
previous_name = Reference(prefix="OMO", identifier="0003008", name="previous name")
legal_name = Reference(prefix="OMO", identifier="0003009", name="legal name")
inn = Reference(prefix="OMO", identifier="0003010", name="International Nonproprietary Name")
latin_term = Reference(prefix="OMO", identifier="0003011", name="latin term")
acronym = Reference(prefix="OMO", identifier="0003012", name="acronym")
#: Provisional, see https://github.com/information-artifact-ontology/ontology-metadata/pull/162/files
brand_name = Reference(prefix="OMO", identifier="0003013", name="brand name")

#: A set of synonym types from OMO
synonym_types: set[Reference] = {
    abbreviation,
    ambiguous_synonym,
    dubious_synonym,
    layperson_synonym,
    plural_form,
    uk_spelling,
    misspelling,
    misnomer,
    previous_name,
    legal_name,
    inn,
    latin_term,
    acronym,
    brand_name,
}

# Semantic Mappings

## Mapping Relations

#: The parent property for semantic mappings from ``skos``, see :data:`semantic_mapping_scopes`
#: for a list of all usable properties
match = Reference(prefix="skos", identifier="mappingRelation", name="is in mapping relation with")

exact_match = Reference(prefix="skos", identifier="exactMatch", name="exact match")
narrow_match = Reference(prefix="skos", identifier="narrowMatch", name="narrow match")
broad_match = Reference(prefix="skos", identifier="broadMatch", name="broad match")
close_match = Reference(prefix="skos", identifier="closeMatch", name="close match")
related_match = Reference(prefix="skos", identifier="relatedMatch", name="related match")

#: A list of strings used to refer to mapping types in ``skos``
SemanticMappingScope: TypeAlias = Literal["EXACT", "NARROW", "BROAD", "CLOSE", "RELATED"]

#: A mapping from mapping types to references
semantic_mapping_scopes: dict[SemanticMappingScope, Reference] = {
    "EXACT": exact_match,
    "NARROW": narrow_match,
    "BROAD": broad_match,
    "CLOSE": close_match,
    "RELATED": related_match,
}

## Matching Process Types

#: The parent class for matching processes, see :data:`matching_processes`
#: for the set of all matching processes.
matching_process = Reference(prefix="semapv", identifier="Matching", name="matching process")

background_knowledge_based_matching_process = Reference(
    prefix="semapv",
    identifier="BackgroundKnowledgeBasedMatching",
    name="background knowledge-based matching process",
)
composite_matching_process = Reference(
    prefix="semapv", identifier="CompositeMatching", name="composite matching process"
)
instance_based_matching_process = Reference(
    prefix="semapv", identifier="InstanceBasedMatching", name="instance-based matching process"
)
lexical_matching_process = Reference(
    prefix="semapv", identifier="LexicalMatching", name="lexical matching process"
)
lexical_similarity_threshold_based_matching_process = Reference(
    prefix="semapv",
    identifier="LexicalSimilarityThresholdMatching",
    name="lexical similarity threshold-based matching process",
)
logical_reasoning_matching_process = Reference(
    prefix="semapv", identifier="LogicalReasoning", name="logical reasoning matching process"
)
manual_mapping_curation = Reference(
    prefix="semapv", identifier="ManualMappingCuration", name="manual mapping curation"
)
mapping_chaining = Reference(
    prefix="semapv", identifier="MappingChaining", name="mapping chaining-based matching process"
)
mapping_inversion = Reference(
    prefix="semapv", identifier="MappingInversion", name="mapping inversion-based matching process"
)
semantic_similarity = Reference(
    prefix="semapv",
    identifier="SemanticSimilarityThresholdMatching",
    name="semantic similarity threshold-based matching process",
)
structural_matching = Reference(
    prefix="semapv", identifier="StructuralMatching", name="structural matching process"
)
unspecified_matching_process = Reference(
    prefix="semapv", identifier="UnspecifiedMatching", name="unspecified matching process"
)

#: A set of matching types from ``semapv``
matching_processes: set[Reference] = {
    background_knowledge_based_matching_process,
    composite_matching_process,
    instance_based_matching_process,
    lexical_matching_process,
    lexical_similarity_threshold_based_matching_process,
    logical_reasoning_matching_process,
    manual_mapping_curation,
    mapping_chaining,
    mapping_inversion,
    semantic_similarity,
    structural_matching,
    unspecified_matching_process,
}

# Individuals

#: the author of this package. It's useful to have this reference pre-defined
#: for testing purposes
charlie = Reference(prefix="orcid", identifier="0000-0003-4423-4370", name="Charles Tapley Hoyt")
