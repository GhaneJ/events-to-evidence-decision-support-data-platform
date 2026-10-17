from __future__ import annotations

from collections.abc import Iterable, Mapping

from .domain import Assessment, EvidenceClassification, EvidenceItem, EvidenceStatement


class EvidenceRuleViolation(ValueError):
    """Raised when an assessment violates the evidence methodology."""


def independent_family_count(items: Iterable[EvidenceItem]) -> int:
    """Count independent evidence families, not publications or records."""
    return len({item.evidence_family_id for item in items if not item.is_synthetic_test})


def validate_assessment(
    assessment: Assessment,
    statements: Mapping[str, EvidenceStatement],
    evidence_items: Mapping[str, EvidenceItem],
) -> None:
    if not assessment.counter_evidence_checked:
        raise EvidenceRuleViolation("counter-evidence check must be recorded before assessment")

    referenced_items: list[EvidenceItem] = []

    for statement_id in assessment.statement_ids:
        try:
            statement = statements[statement_id]
        except KeyError as exc:
            raise EvidenceRuleViolation(f"unknown evidence statement: {statement_id}") from exc

        for item_id in statement.evidence_item_ids:
            try:
                item = evidence_items[item_id]
            except KeyError as exc:
                raise EvidenceRuleViolation(f"unknown evidence item: {item_id}") from exc

            if item.is_synthetic_test:
                raise EvidenceRuleViolation(
                    "synthetic technical-test evidence cannot support a societal assessment"
                )
            if item.generated_by_ai:
                raise EvidenceRuleViolation("AI-generated content cannot be assessment evidence")
            referenced_items.append(item)

    if assessment.classification == EvidenceClassification.SUPPORTED_INTERPRETATION:
        if independent_family_count(referenced_items) < 2:
            raise EvidenceRuleViolation(
                "supported interpretation requires at least two independent evidence families"
            )
