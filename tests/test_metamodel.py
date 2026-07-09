"""Test the lightweight metadata model."""

import datetime
import unittest
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from curies import NamableReference, Reference, vocabulary
from curies.metamodel import iter_records


class TestModel(unittest.TestCase):
    """Test parsing models."""

    def test_model(self) -> None:
        """Test parsing into a namable reference."""

        class MM(BaseModel):
            """Test model."""

            curie: NamableReference

        names = {"curie": "curie_label"}
        records = [
            {"curie": "GO:0000001", "curie_label": "Test 1"},
            {"curie": "GO:0000002", "curie_label": "Test 2"},
        ]

        models = list(iter_records(records, MM, names=names))
        self.assertEqual(
            [
                MM(curie=NamableReference(prefix="GO", identifier="0000001", name="Test 1")),
                MM(curie=NamableReference(prefix="GO", identifier="0000002", name="Test 2")),
            ],
            models,
        )

    def test_model_with_aliases(self) -> None:
        """Test metamodel that has aliases."""

        class SemanticMapping(BaseModel):
            """A model for SSSOM semantic mapping."""

            model_config = ConfigDict(
                populate_by_name=True,
            )

            subject: NamableReference = Field(..., alias="subject_id")
            predicate: NamableReference = Field(..., alias="predicate_id")
            predicate_modifier: Literal["Not"] | None = Field(None)
            object: NamableReference = Field(..., alias="object_id")
            mapping_justification: Reference = Field(...)
            license: Reference | None = Field(None)
            creator: NamableReference | None = Field(None, alias="creator_id")
            author: NamableReference | None = Field(None, alias="author_id")
            reviewer: NamableReference | None = Field(None, alias="reviewer_id")
            publication_date: datetime.date | None = Field(None)
            issue_tracker_item: str | None = Field(None)
            comment: str | None = Field(None)

        records = [
            {
                "subject_id": "CHEBI:16236",
                "subject_label": "ethanol",
                "predicate_id": "skos:exactMatch",
                "object_id": "pubchem.compound:702",
                "mapping_justification": "semapv:ManualMappingCuration",
            },
            {
                "subject_id": "CHEBI:28831",
                "subject_label": "propanol",
                "predicate_id": "skos:exactMatch",
                "object_id": "pubchem.compound:1031",
                "mapping_justification": "semapv:ManualMappingCuration",
            },
            {
                "subject_id": "CHEBI:44884",
                "subject_label": "pentanol",
                "predicate_id": "skos:exactMatch",
                "object_id": "pubchem.compound:6276",
                "mapping_justification": "semapv:ManualMappingCuration",
            },
        ]

        models = list(
            iter_records(
                records,
                SemanticMapping,
                names={
                    "subject_id": "subject_label",
                    "predicate_id": "predicate_label",
                    "object_id": "object_label",
                    "author_id": "author_label",
                    "reviewer_id": "reviewer_label",
                    "creator_id": "creator_label",
                },
            )
        )

        exact_match = NamableReference.from_reference(vocabulary.exact_match)
        self.assertEqual(
            [
                SemanticMapping(
                    subject=NamableReference.from_curie("CHEBI:16236", name="ethanol"),
                    predicate=exact_match,
                    object=NamableReference.from_curie("pubchem.compound:702"),
                    mapping_justification=vocabulary.manual_mapping_curation,
                ),
                SemanticMapping(
                    subject=NamableReference.from_curie("CHEBI:28831", name="propanol"),
                    predicate=exact_match,
                    object=NamableReference.from_curie("pubchem.compound:1031"),
                    mapping_justification=vocabulary.manual_mapping_curation,
                ),
                SemanticMapping(
                    subject=NamableReference.from_curie("CHEBI:44884", name="pentanol"),
                    predicate=exact_match,
                    object=NamableReference.from_curie("pubchem.compound:6276"),
                    mapping_justification=vocabulary.manual_mapping_curation,
                ),
            ],
            models,
        )
