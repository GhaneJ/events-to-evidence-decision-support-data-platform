import pytest

from evidence_intelligence.domain import EvidenceClassification, EvidenceDirection
from evidence_intelligence.persistence.evidence_statement_sqlserver import (
    CohortStatementInput,
    prepare_jobstream_experience_statement,
)


BATCH_ID = "af-jobstream-20261018T092402Z-db19ff70"
TRANSFORMATION_ID = f"experience-audit:{BATCH_ID}"
REQUEST_PARAMETERS = {
    "updated_after": "2026-10-17T00:00:00",
    "updated_before": "2026-10-18T00:00:00",
}


def _row(index: int, status: str, transformation_id: str = TRANSFORMATION_ID):
    return CohortStatementInput(
        evidence_item_id=f"evidence-{index}",
        experience_signal_status=status,
        transformation_id=transformation_id,
    )


def test_prepare_statement_is_batch_bounded_observed_fact_with_derivation() -> None:
    rows = [
        *(_row(index, "explicit_threshold_or_seniority") for index in range(1, 8)),
        *(_row(index, "qualitative_experience_only") for index in range(8, 10)),
    ]

    statement = prepare_jobstream_experience_statement(
        batch_id=BATCH_ID,
        request_parameters=REQUEST_PARAMETERS,
        cohort_rows=rows,
    )

    assert statement.classification == EvidenceClassification.OBSERVED_FACT
    assert statement.direction == EvidenceDirection.CONTEXT
    assert len(statement.evidence_item_ids) == 9
    assert statement.transformation_ids == (TRANSFORMATION_ID,)
    assert "24-hour" in statement.text
    assert "7 contained an explicit quantified experience threshold" in statement.text
    assert "2 contained qualitative experience language only" in statement.text
    assert "does not establish" in statement.text
    assert "wider Swedish software-development labor market" in statement.text
    assert "not used here as an accessibility conclusion" in statement.text


def test_prepare_statement_rejects_mixed_derivation_transformations() -> None:
    rows = [
        _row(1, "explicit_threshold_or_seniority"),
        _row(2, "qualitative_experience_only", "other-transformation"),
    ]

    with pytest.raises(ValueError, match="exactly one"):
        prepare_jobstream_experience_statement(
            batch_id=BATCH_ID,
            request_parameters=REQUEST_PARAMETERS,
            cohort_rows=rows,
        )


def test_prepare_statement_rejects_unknown_status_vocabulary() -> None:
    with pytest.raises(ValueError, match="unexpected experience-signal status"):
        prepare_jobstream_experience_statement(
            batch_id=BATCH_ID,
            request_parameters=REQUEST_PARAMETERS,
            cohort_rows=[_row(1, "junior_friendly")],
        )
