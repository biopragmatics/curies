"""A module containing pre-defined references."""

from typing import Literal
from curies import NamedReference as Reference

# Synonyms

## Synonym Relations

has_synonym = Reference(prefix="oboInOwl", identifier="hasSynonym", name="has synonym")
has_exact_synonym = Reference(prefix="oboInOwl", identifier="hasExactSynonym", name="has exact synonym")
has_narrow_synonym = Reference(prefix="oboInOwl", identifier="hasNarrowSynonym", name="has narrow synonym")
has_broad_synonym = Reference(prefix="oboInOwl", identifier="hasBroadSynonym", name="has broad synonym")
has_related_synonym = Reference(prefix="oboInOwl", identifier="hasRelatedSynonym", name="has related synonym")

SynonymScope = Literal["EXACT", "NARROW", "BROAD", "RELATED"]

#: A mapping from synonym scopes to th
SYNONYM: dict[SynonymScope, Reference] = {
    "EXACT": has_exact_synonym,
    "NARROW": has_narrow_synonym,
    "BROAD": has_broad_synonym,
    "RELATED": has_related_synonym,
}

## OMO Synonym Types

synonym_type = Reference(prefix="oboInOwl", identifier="SynonymType", name="synonym type")
abbreviation = Reference(prefix="OMO", identifier="0003000", name="abbreviation")
acronym = Reference(prefix="omo", identifier="0003012", name="acronym")
uk_spelling = Reference(prefix="omo", identifier="0003005", name="UK spelling synonym")

# Semantic Mappings

## Matching Types

unspecified_matching = Reference(
    prefix="semapv", identifier="UnspecifiedMatching", name="unspecified matching process"
)