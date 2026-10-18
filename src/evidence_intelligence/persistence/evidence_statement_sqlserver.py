from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from ..domain import EvidenceClassification, EvidenceDirection, EvidenceStatement
from .jobstream_sqlserver import build_sqlserver_connection_string


@dataclass(frozen=True, slots=True)
class CohortStatementInput:
    evidence_item_id: str
    experience_signal_status: str
    transformation_id: str


@dataclass(frozen=True, slots=True)
class StatementLoadReport:
    statement_id: str
    classification: str
    direction: str
    evidence_items: int
    derivations: int
    explicit_threshold_or_seniority: int
    qualitative_experience_only: int
    meritorious_experience_only: int
    unknown: int

    def as_dict(self) -> dict[str, int | str]:
        return {
            "statement_id": self.statement_id,
            "classification": self.classification,
            "direction": self.direction,
            "evidence_items": self.evidence_items,
            "derivations": self.derivations,
            "explicit_threshold_or_seniority": self.explicit_threshold_or_seniority,
            "qualitative_experience_only": self.qualitative_experience_only,
            "meritorious_experience_only": self.meritorious_experience_only,
            "unknown": self.unknown,
        }


_ALLOWED_STATUSES = {
    "explicit_threshold_or_seniority",
    "qualitative_experience_only",
    "meritorious_experience_only",
    "unknown",
}


def _window_hours(request_parameters: dict[str, Any]) -> float | None:
    start = request_parameters.get("updated_after")
    end = request_parameters.get("updated_before")
    if not isinstance(start, str) or not isinstance(end, str):
        return None
    try:
        delta = datetime.fromisoformat(end) - datetime.fromisoformat(start)
    except ValueError:
        return None
    return delta.total_seconds() / 3600


def _window_label(request_parameters: dict[str, Any]) -> str:
    hours = _window_hours(request_parameters)
    if hours is not None and hours > 0 and abs(hours - round(hours)) < 1e-9:
        return f"{int(round(hours))}-hour"
    return "bounded"


def prepare_jobstream_experience_statement(
    *,
    batch_id: str,
    request_parameters: dict[str, Any],
    cohort_rows: Iterable[CohortStatementInput],
) -> EvidenceStatement:
    rows = tuple(cohort_rows)
    if not rows:
        raise ValueError("cannot create an evidence statement from an empty analytical cohort")

    item_ids = tuple(row.evidence_item_id for row in rows)
    if len(set(item_ids)) != len(item_ids):
        raise ValueError("analytical cohort contains duplicate evidence item ids")

    statuses = [row.experience_signal_status for row in rows]
    unexpected = sorted(set(statuses) - _ALLOWED_STATUSES)
    if unexpected:
        raise ValueError(f"unexpected experience-signal status: {', '.join(unexpected)}")

    transformation_ids = tuple(sorted({row.transformation_id for row in rows}))
    if len(transformation_ids) != 1:
        raise ValueError(
            "batch-bounded statement requires exactly one deterministic derivation transformation"
        )

    counts = Counter(statuses)
    pieces: list[str] = []
    if counts["explicit_threshold_or_seniority"]:
        pieces.append(
            f"{counts['explicit_threshold_or_seniority']} contained an explicit quantified "
            "experience threshold and/or constrained seniority signal"
        )
    if counts["qualitative_experience_only"]:
        pieces.append(
            f"{counts['qualitative_experience_only']} contained qualitative experience "
            "language only"
        )
    if counts["meritorious_experience_only"]:
        pieces.append(
            f"{counts['meritorious_experience_only']} contained only meritorious experience "
            "language"
        )
    if counts["unknown"]:
        pieces.append(
            f"{counts['unknown']} had no detected experience signal and therefore remain unknown"
        )

    if len(pieces) == 1:
        distribution = pieces[0]
    else:
        distribution = ", ".join(pieces[:-1]) + ", while " + pieces[-1]

    text = (
        f"In the {_window_label(request_parameters)} Arbetsförmedlingen JobStream batch "
        f"{batch_id}, the analytical cohort contained {len(rows)} full advertisements: "
        f"{distribution}. This is a batch-bounded observed fact from one JobStream batch; "
        "it does not establish that the same distribution characterizes the wider Swedish "
        "software-development labor market. The provider's raw experience_required value "
        "is preserved as source data but is not used here as an accessibility conclusion."
    )

    return EvidenceStatement(
        statement_id=f"jobstream-experience-observation:{batch_id}",
        text=text,
        direction=EvidenceDirection.CONTEXT,
        classification=EvidenceClassification.OBSERVED_FACT,
        evidence_item_ids=tuple(sorted(item_ids)),
        transformation_ids=transformation_ids,
    )


def _fetch_statement_inputs(cursor: Any, batch_id: str) -> tuple[dict[str, Any], tuple[CohortStatementInput, ...]]:
    batch = cursor.execute(
        """
        SELECT request_parameters
        FROM dbo.ingestion_batch
        WHERE batch_id = ?
        """,
        batch_id,
    ).fetchone()
    if batch is None:
        raise ValueError(f"unknown ingestion batch: {batch_id}")

    request_parameters = json.loads(batch[0])
    if not isinstance(request_parameters, dict):
        raise ValueError("ingestion batch request_parameters must be a JSON object")

    rows = cursor.execute(
        """
        SELECT
            e.evidence_item_id,
            o.experience_signal_status,
            o.experience_audit_transformation_id
        FROM dbo.evidence_item e
        INNER JOIN dbo.job_ad_observation o
            ON o.evidence_item_id = e.evidence_item_id
        WHERE e.batch_id = ?
          AND o.is_in_analytical_cohort = 1
        ORDER BY e.evidence_item_id
        """,
        batch_id,
    ).fetchall()

    inputs: list[CohortStatementInput] = []
    for row in rows:
        if row[1] is None or row[2] is None:
            raise ValueError(
                f"in-cohort evidence item {row[0]} is missing validated experience derivation"
            )
        inputs.append(
            CohortStatementInput(
                evidence_item_id=str(row[0]),
                experience_signal_status=str(row[1]),
                transformation_id=str(row[2]),
            )
        )

    return request_parameters, tuple(inputs)


def _verify_existing_statement(cursor: Any, statement: EvidenceStatement) -> None:
    row = cursor.execute(
        """
        SELECT statement_text, direction, classification
        FROM dbo.evidence_statement
        WHERE statement_id = ?
        """,
        statement.statement_id,
    ).fetchone()
    if row is None:
        return

    actual = (str(row[0]), str(row[1]), str(row[2]))
    expected = (
        statement.text,
        statement.direction.value,
        statement.classification.value,
    )
    if actual != expected:
        raise ValueError(
            f"existing evidence statement conflicts with prepared statement {statement.statement_id}"
        )


def _insert_if_missing(
    cursor: Any,
    *,
    existence_sql: str,
    existence_params: tuple[Any, ...],
    insert_sql: str,
    insert_params: tuple[Any, ...],
) -> None:
    if cursor.execute(existence_sql, existence_params).fetchone() is None:
        cursor.execute(insert_sql, insert_params)


def persist_jobstream_experience_statement(
    connection: Any,
    *,
    batch_id: str,
) -> StatementLoadReport:
    cursor = connection.cursor()
    try:
        request_parameters, inputs = _fetch_statement_inputs(cursor, batch_id)
        statement = prepare_jobstream_experience_statement(
            batch_id=batch_id,
            request_parameters=request_parameters,
            cohort_rows=inputs,
        )

        _verify_existing_statement(cursor, statement)

        _insert_if_missing(
            cursor,
            existence_sql="SELECT 1 FROM dbo.evidence_statement WHERE statement_id = ?",
            existence_params=(statement.statement_id,),
            insert_sql="""
                INSERT INTO dbo.evidence_statement
                    (statement_id, statement_text, direction, classification)
                VALUES (?, ?, ?, ?)
            """,
            insert_params=(
                statement.statement_id,
                statement.text,
                statement.direction.value,
                statement.classification.value,
            ),
        )

        for evidence_item_id in statement.evidence_item_ids:
            _insert_if_missing(
                cursor,
                existence_sql="""
                    SELECT 1
                    FROM dbo.statement_evidence
                    WHERE statement_id = ? AND evidence_item_id = ?
                """,
                existence_params=(statement.statement_id, evidence_item_id),
                insert_sql="""
                    INSERT INTO dbo.statement_evidence
                        (statement_id, evidence_item_id)
                    VALUES (?, ?)
                """,
                insert_params=(statement.statement_id, evidence_item_id),
            )

        for transformation_id in statement.transformation_ids:
            _insert_if_missing(
                cursor,
                existence_sql="""
                    SELECT 1
                    FROM dbo.evidence_statement_derivation
                    WHERE statement_id = ? AND transformation_id = ?
                """,
                existence_params=(statement.statement_id, transformation_id),
                insert_sql="""
                    INSERT INTO dbo.evidence_statement_derivation
                        (statement_id, transformation_id)
                    VALUES (?, ?)
                """,
                insert_params=(statement.statement_id, transformation_id),
            )

        persisted_items = {
            str(row[0])
            for row in cursor.execute(
                """
                SELECT evidence_item_id
                FROM dbo.statement_evidence
                WHERE statement_id = ?
                """,
                statement.statement_id,
            ).fetchall()
        }
        expected_items = set(statement.evidence_item_ids)
        if persisted_items != expected_items:
            raise ValueError(
                "post-load statement evidence links do not exactly match the prepared cohort"
            )

        persisted_derivations = {
            str(row[0])
            for row in cursor.execute(
                """
                SELECT transformation_id
                FROM dbo.evidence_statement_derivation
                WHERE statement_id = ?
                """,
                statement.statement_id,
            ).fetchall()
        }
        expected_derivations = set(statement.transformation_ids)
        if persisted_derivations != expected_derivations:
            raise ValueError(
                "post-load statement derivation links do not exactly match the prepared lineage"
            )

        counts = Counter(row.experience_signal_status for row in inputs)
        connection.commit()
        return StatementLoadReport(
            statement_id=statement.statement_id,
            classification=statement.classification.value,
            direction=statement.direction.value,
            evidence_items=len(persisted_items),
            derivations=len(persisted_derivations),
            explicit_threshold_or_seniority=counts["explicit_threshold_or_seniority"],
            qualitative_experience_only=counts["qualitative_experience_only"],
            meritorious_experience_only=counts["meritorious_experience_only"],
            unknown=counts["unknown"],
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def persist_jobstream_experience_statement_sqlserver(
    *,
    batch_id: str,
    server: str = "localhost",
    database: str = "EventsToEvidence_Dev",
    driver: str = "ODBC Driver 18 for SQL Server",
) -> StatementLoadReport:
    try:
        import pyodbc
    except ImportError as exc:
        raise RuntimeError(
            'pyodbc is required for SQL Server persistence; run pip install -e ".[dev]"'
        ) from exc

    connection = pyodbc.connect(
        build_sqlserver_connection_string(
            server=server,
            database=database,
            driver=driver,
        ),
        autocommit=False,
    )
    try:
        return persist_jobstream_experience_statement(
            connection,
            batch_id=batch_id,
        )
    finally:
        connection.close()
