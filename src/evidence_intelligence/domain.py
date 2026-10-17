from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class EvidenceClassification(StrEnum):
    OBSERVED_FACT = "observed_fact"
    STATISTICAL_ASSOCIATION = "statistical_association"
    SUPPORTED_INTERPRETATION = "supported_interpretation"
    HYPOTHESIS = "hypothesis"
    CONTESTED_EXPLANATION = "contested_explanation"
    UNRESOLVED_QUESTION = "unresolved_question"


class EvidenceDirection(StrEnum):
    SUPPORT = "support"
    CONFLICT = "conflict"
    CONTEXT = "context"


class SourceKind(StrEnum):
    OBSERVED_JOB_ADS = "observed_job_ads"
    OFFICIAL_STATISTICS = "official_statistics"
    ADMINISTRATIVE_OUTCOME = "administrative_outcome"
    EMPLOYER_SURVEY = "employer_survey"
    RESEARCH = "research"
    OTHER = "other"


def _required(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_name} is required")


@dataclass(frozen=True, slots=True)
class InvestigationQuestion:
    question_id: str
    text: str
    decision_context: str

    def __post_init__(self) -> None:
        _required(self.question_id, "question_id")
        _required(self.text, "text")
        _required(self.decision_context, "decision_context")


@dataclass(frozen=True, slots=True)
class EvidenceFamily:
    family_id: str
    name: str
    ancestry_note: str

    def __post_init__(self) -> None:
        _required(self.family_id, "family_id")
        _required(self.name, "name")
        _required(self.ancestry_note, "ancestry_note")


@dataclass(frozen=True, slots=True)
class Source:
    source_id: str
    name: str
    publisher: str
    url: str
    kind: SourceKind
    evidence_family_id: str
    collection_method: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.source_id, "source_id"),
            (self.name, "name"),
            (self.publisher, "publisher"),
            (self.url, "url"),
            (self.evidence_family_id, "evidence_family_id"),
            (self.collection_method, "collection_method"),
        ):
            _required(value, name)


@dataclass(frozen=True, slots=True)
class IngestionBatch:
    batch_id: str
    source_id: str
    endpoint: str
    retrieved_at: datetime
    raw_location: str
    raw_fingerprint: str
    record_count: int

    def __post_init__(self) -> None:
        for value, name in (
            (self.batch_id, "batch_id"),
            (self.source_id, "source_id"),
            (self.endpoint, "endpoint"),
            (self.raw_location, "raw_location"),
            (self.raw_fingerprint, "raw_fingerprint"),
        ):
            _required(value, name)
        if self.record_count < 0:
            raise ValueError("record_count must be non-negative")


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    evidence_item_id: str
    source_id: str
    evidence_family_id: str
    source_record_id: str
    retrieved_at: datetime
    raw_fingerprint: str
    observed_at: datetime | None = None
    is_synthetic_test: bool = False
    generated_by_ai: bool = False

    def __post_init__(self) -> None:
        for value, name in (
            (self.evidence_item_id, "evidence_item_id"),
            (self.source_id, "source_id"),
            (self.evidence_family_id, "evidence_family_id"),
            (self.source_record_id, "source_record_id"),
            (self.raw_fingerprint, "raw_fingerprint"),
        ):
            _required(value, name)
        if self.generated_by_ai:
            raise ValueError("AI-generated content cannot be stored as societal evidence")


@dataclass(frozen=True, slots=True)
class Transformation:
    transformation_id: str
    name: str
    code_version: str
    description: str
    input_evidence_item_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, name in (
            (self.transformation_id, "transformation_id"),
            (self.name, "name"),
            (self.code_version, "code_version"),
            (self.description, "description"),
        ):
            _required(value, name)
        if not self.input_evidence_item_ids:
            raise ValueError("transformation requires at least one input evidence item")


@dataclass(frozen=True, slots=True)
class EvidenceStatement:
    statement_id: str
    text: str
    direction: EvidenceDirection
    classification: EvidenceClassification
    evidence_item_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _required(self.statement_id, "statement_id")
        _required(self.text, "text")
        if not self.evidence_item_ids:
            raise ValueError("evidence statement requires at least one evidence item")


@dataclass(frozen=True, slots=True)
class Assessment:
    assessment_id: str
    question_id: str
    classification: EvidenceClassification
    statement_ids: tuple[str, ...]
    uncertainty: str
    counter_evidence_checked: bool

    def __post_init__(self) -> None:
        _required(self.assessment_id, "assessment_id")
        _required(self.question_id, "question_id")
        _required(self.uncertainty, "uncertainty")
        if not self.statement_ids:
            raise ValueError("assessment requires at least one evidence statement")


@dataclass(frozen=True, slots=True)
class DecisionArtifact:
    artifact_id: str
    assessment_id: str
    intended_use: str
    generated_at: datetime

    def __post_init__(self) -> None:
        _required(self.artifact_id, "artifact_id")
        _required(self.assessment_id, "assessment_id")
        _required(self.intended_use, "intended_use")
