from datetime import UTC, datetime

import pytest

from evidence_intelligence.domain import (
    Assessment,
    EvidenceClassification,
    EvidenceDirection,
    EvidenceItem,
    EvidenceStatement,
)
from evidence_intelligence.evidence_rules import (
    EvidenceRuleViolation,
    independent_family_count,
    validate_assessment,
)


NOW = datetime(2026, 10, 17, 15, 0, tzinfo=UTC)


def item(item_id: str, family: str, *, synthetic: bool = False) -> EvidenceItem:
    return EvidenceItem(
        evidence_item_id=item_id,
        source_id=f"source-{family}",
        evidence_family_id=family,
        source_record_id=f"record-{item_id}",
        retrieved_at=NOW,
        raw_fingerprint=(item_id * 64)[:64],
        is_synthetic_test=synthetic,
    )


def statement(statement_id: str, *item_ids: str) -> EvidenceStatement:
    return EvidenceStatement(
        statement_id=statement_id,
        text="Test statement",
        direction=EvidenceDirection.SUPPORT,
        classification=EvidenceClassification.SUPPORTED_INTERPRETATION,
        evidence_item_ids=tuple(item_ids),
    )


def assessment(*statement_ids: str, counter_evidence_checked: bool = True) -> Assessment:
    return Assessment(
        assessment_id="a-1",
        question_id="q-1",
        classification=EvidenceClassification.SUPPORTED_INTERPRETATION,
        statement_ids=tuple(statement_ids),
        uncertainty="Field completeness is not yet known.",
        counter_evidence_checked=counter_evidence_checked,
    )


def test_repeated_records_from_one_family_count_once() -> None:
    assert independent_family_count([item("1", "family-a"), item("2", "family-a")]) == 1


def test_supported_interpretation_requires_independent_families() -> None:
    items = {"1": item("1", "family-a"), "2": item("2", "family-a")}
    statements = {"s-1": statement("s-1", "1", "2")}

    with pytest.raises(EvidenceRuleViolation, match="two independent evidence families"):
        validate_assessment(assessment("s-1"), statements, items)


def test_supported_interpretation_accepts_two_families() -> None:
    items = {"1": item("1", "family-a"), "2": item("2", "family-b")}
    statements = {"s-1": statement("s-1", "1", "2")}
    validate_assessment(assessment("s-1"), statements, items)


def test_counter_evidence_check_is_required() -> None:
    items = {"1": item("1", "family-a"), "2": item("2", "family-b")}
    statements = {"s-1": statement("s-1", "1", "2")}

    with pytest.raises(EvidenceRuleViolation, match="counter-evidence"):
        validate_assessment(
            assessment("s-1", counter_evidence_checked=False),
            statements,
            items,
        )


def test_synthetic_test_data_cannot_support_societal_assessment() -> None:
    items = {"1": item("1", "family-a", synthetic=True), "2": item("2", "family-b")}
    statements = {"s-1": statement("s-1", "1", "2")}

    with pytest.raises(EvidenceRuleViolation, match="synthetic technical-test evidence"):
        validate_assessment(assessment("s-1"), statements, items)


def test_ai_generated_evidence_is_rejected_at_creation() -> None:
    with pytest.raises(ValueError, match="AI-generated"):
        EvidenceItem(
            evidence_item_id="ai-1",
            source_id="source-ai",
            evidence_family_id="family-ai",
            source_record_id="record-ai",
            retrieved_at=NOW,
            raw_fingerprint="a" * 64,
            generated_by_ai=True,
        )
