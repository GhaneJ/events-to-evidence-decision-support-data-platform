from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..profiling.experience_signals import (
    SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID,
    audit_experience_signals_jsonl,
)

OBSERVED_JOB_ADS_FAMILY_ID = "observed-public-job-advertisements"
ANALYTICAL_COHORT_NAME = "Mjukvaru- och systemutvecklare m.fl. (2512)"
EXPERIENCE_AUDIT_VERSION = "experience-signals-v1"
JOBSTREAM_SOURCE_NAME = "Arbetsförmedlingen JobStream v2"
JOBSTREAM_PUBLISHER = "Arbetsförmedlingen"
JOBSTREAM_BASE_URL = "https://jobstream.api.jobtechdev.se"


@dataclass(frozen=True, slots=True)
class PreparedAd:
    evidence_item_id: str
    source_record_id: str
    raw_fingerprint: str
    raw_location: str
    observed_at: str | None
    headline: str | None
    occupation_concept_id: str | None
    occupation_label: str | None
    occupation_group_concept_id: str | None
    occupation_group_label: str | None
    occupation_field_concept_id: str | None
    occupation_field_label: str | None
    provider_experience_required: bool | None
    is_in_analytical_cohort: bool
    experience_signal_status: str | None
    signals: tuple[dict[str, str], ...]


@dataclass(frozen=True, slots=True)
class PreparedBatch:
    manifest: dict[str, Any]
    data_path: Path
    cohort_id: str
    transformation_id: str
    ads: tuple[PreparedAd, ...]

    @property
    def in_cohort_count(self) -> int:
        return sum(ad.is_in_analytical_cohort for ad in self.ads)


@dataclass(frozen=True, slots=True)
class LoadReport:
    batch_id: str
    raw_records: int
    full_ads: int
    cohort_ads: int
    out_of_cohort_ads: int
    transformation_inputs: int
    persisted_signals: int

    def as_dict(self) -> dict[str, int | str]:
        return {
            "batch_id": self.batch_id,
            "raw_records": self.raw_records,
            "full_ads": self.full_ads,
            "cohort_ads": self.cohort_ads,
            "out_of_cohort_ads": self.out_of_cohort_ads,
            "transformation_inputs": self.transformation_inputs,
            "persisted_signals": self.persisted_signals,
        }


def build_sqlserver_connection_string(
    *,
    server: str,
    database: str,
    driver: str = "ODBC Driver 18 for SQL Server",
) -> str:
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes"
    )


def _ad_payload(record: dict[str, Any]) -> dict[str, Any]:
    for key in ("ad", "data", "payload"):
        value = record.get(key)
        if isinstance(value, dict):
            return value
    return record


def _concept_id(value: object) -> str | None:
    if isinstance(value, dict):
        concept_id = value.get("concept_id")
        if isinstance(concept_id, str) and concept_id:
            return concept_id
    return None


def _label(value: object) -> str | None:
    if isinstance(value, dict):
        label = value.get("label")
        if isinstance(label, str) and label:
            return label
    return None


def _record_id(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, int):
        return str(value)
    return None


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _read_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest must be a JSON object")

    required = (
        "batch_id",
        "source_id",
        "endpoint",
        "retrieved_at",
        "request_parameters",
        "record_count",
        "raw_sha256",
        "data_file",
    )
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(f"manifest missing required fields: {', '.join(missing)}")
    return payload


def prepare_jobstream_batch(
    manifest_path: Path,
    *,
    occupation_group_id: str = SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID,
) -> PreparedBatch:
    manifest = _read_manifest(manifest_path)
    data_path = manifest_path.parent / str(manifest["data_file"])
    if not data_path.is_file():
        raise FileNotFoundError(f"raw data file not found: {data_path}")

    raw_bytes = data_path.read_bytes()
    actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if actual_sha256 != manifest["raw_sha256"]:
        raise ValueError(
            f"raw SHA-256 mismatch: manifest={manifest['raw_sha256']} actual={actual_sha256}"
        )

    lines = [line for line in raw_bytes.decode("utf-8").splitlines() if line.strip()]
    if len(lines) != manifest["record_count"]:
        raise ValueError(
            f"raw record count mismatch: manifest={manifest['record_count']} actual={len(lines)}"
        )

    audit = audit_experience_signals_jsonl(
        data_path,
        occupation_group_id=occupation_group_id,
    )
    audits_by_id = {ad.ad_id: ad for ad in audit.ads if ad.ad_id is not None}

    batch_id = str(manifest["batch_id"])
    source_id = str(manifest["source_id"])
    cohort_id = f"{source_id}:occupation-group:{occupation_group_id}"
    transformation_id = f"experience-audit:{batch_id}"
    raw_path = data_path.as_posix()

    ads: list[PreparedAd] = []
    for line_number, raw_line in enumerate(lines, start=1):
        record = json.loads(raw_line)
        if not isinstance(record, dict):
            continue

        ad = _ad_payload(record)
        is_removed = record.get("removed") is True or ad.get("removed") is True
        if is_removed:
            continue

        source_record_id = _record_id(ad.get("id"))
        if source_record_id is None:
            raise ValueError(f"full advertisement at line {line_number} has no usable id")

        occupation = ad.get("occupation")
        occupation_group = ad.get("occupation_group")
        occupation_field = ad.get("occupation_field")
        group_id = _concept_id(occupation_group)
        in_cohort = group_id == occupation_group_id

        provider_value = ad.get("experience_required")
        provider_experience_required = (
            provider_value if isinstance(provider_value, bool) else None
        )

        audit_ad = audits_by_id.get(source_record_id) if in_cohort else None
        if in_cohort and audit_ad is None:
            raise ValueError(
                f"in-cohort advertisement {source_record_id} is missing from experience audit"
            )

        normalized_line = raw_line.rstrip("\r\n") + "\n"
        record_fingerprint = hashlib.sha256(
            normalized_line.encode("utf-8")
        ).hexdigest()

        ads.append(
            PreparedAd(
                evidence_item_id=f"{batch_id}:{source_record_id}",
                source_record_id=source_record_id,
                raw_fingerprint=record_fingerprint,
                raw_location=f"{raw_path}#line={line_number}",
                observed_at=_optional_text(ad.get("publication_date")),
                headline=_optional_text(ad.get("headline")),
                occupation_concept_id=_concept_id(occupation),
                occupation_label=_label(occupation),
                occupation_group_concept_id=group_id,
                occupation_group_label=_label(occupation_group),
                occupation_field_concept_id=_concept_id(occupation_field),
                occupation_field_label=_label(occupation_field),
                provider_experience_required=provider_experience_required,
                is_in_analytical_cohort=in_cohort,
                experience_signal_status=audit_ad.status if audit_ad else None,
                signals=(
                    tuple(
                        {
                            "category": signal.category,
                            "source_field": signal.source_field,
                            "matched_text": signal.matched_text,
                            "snippet": signal.snippet,
                        }
                        for signal in audit_ad.signals
                    )
                    if audit_ad
                    else ()
                ),
            )
        )

    if len(ads) != audit.full_ad_records:
        raise ValueError(
            f"full-ad preparation mismatch: audit={audit.full_ad_records} prepared={len(ads)}"
        )
    if sum(ad.is_in_analytical_cohort for ad in ads) != audit.cohort_records:
        raise ValueError("analytical-cohort preparation mismatch")

    return PreparedBatch(
        manifest=manifest,
        data_path=data_path,
        cohort_id=cohort_id,
        transformation_id=transformation_id,
        ads=tuple(ads),
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


def _verify_existing_batch(cursor: Any, prepared: PreparedBatch) -> None:
    manifest = prepared.manifest
    row = cursor.execute(
        """
        SELECT source_id, raw_sha256, record_count
        FROM dbo.ingestion_batch
        WHERE batch_id = ?
        """,
        manifest["batch_id"],
    ).fetchone()
    if row is None:
        return

    actual = (row[0], row[1], row[2])
    expected = (
        str(manifest["source_id"]),
        str(manifest["raw_sha256"]),
        int(manifest["record_count"]),
    )
    if actual != expected:
        raise ValueError(
            "existing ingestion_batch conflicts with immutable manifest "
            f"for {manifest['batch_id']}: existing={actual!r} expected={expected!r}"
        )


def load_prepared_jobstream_batch(connection: Any, prepared: PreparedBatch) -> LoadReport:
    manifest = prepared.manifest
    source_id = str(manifest["source_id"])
    endpoint = str(manifest["endpoint"])
    source_url = (
        endpoint
        if endpoint.startswith(("http://", "https://"))
        else f"{JOBSTREAM_BASE_URL}{endpoint}"
    )

    cursor = connection.cursor()
    try:
        _insert_if_missing(
            cursor,
            existence_sql="SELECT 1 FROM dbo.evidence_family WHERE evidence_family_id = ?",
            existence_params=(OBSERVED_JOB_ADS_FAMILY_ID,),
            insert_sql="""
                INSERT INTO dbo.evidence_family
                    (evidence_family_id, name, ancestry_note)
                VALUES (?, ?, ?)
            """,
            insert_params=(
                OBSERVED_JOB_ADS_FAMILY_ID,
                "Observed public job advertisements",
                (
                    "Arbetsförmedlingen JobStream advertisements are one observed-ad evidence "
                    "family; multiple ads do not constitute independent evidence families."
                ),
            ),
        )

        _insert_if_missing(
            cursor,
            existence_sql="SELECT 1 FROM dbo.[source] WHERE source_id = ?",
            existence_params=(source_id,),
            insert_sql="""
                INSERT INTO dbo.[source]
                    (
                        source_id, name, publisher, source_url, source_kind,
                        evidence_family_id, collection_method
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            insert_params=(
                source_id,
                JOBSTREAM_SOURCE_NAME,
                JOBSTREAM_PUBLISHER,
                source_url,
                "observed_job_ads",
                OBSERVED_JOB_ADS_FAMILY_ID,
                "Bounded JobStream v2 NDJSON ingestion with immutable raw landing and manifest.",
            ),
        )

        _verify_existing_batch(cursor, prepared)

        _insert_if_missing(
            cursor,
            existence_sql="SELECT 1 FROM dbo.ingestion_batch WHERE batch_id = ?",
            existence_params=(manifest["batch_id"],),
            insert_sql="""
                INSERT INTO dbo.ingestion_batch
                    (
                        batch_id, source_id, endpoint, request_parameters,
                        retrieved_at, raw_path, raw_sha256, record_count
                    )
                VALUES (?, ?, ?, ?, CAST(? AS datetimeoffset(7)), ?, ?, ?)
            """,
            insert_params=(
                str(manifest["batch_id"]),
                source_id,
                endpoint,
                json.dumps(
                    manifest["request_parameters"],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                str(manifest["retrieved_at"]),
                prepared.data_path.as_posix(),
                str(manifest["raw_sha256"]),
                int(manifest["record_count"]),
            ),
        )

        _insert_if_missing(
            cursor,
            existence_sql="SELECT 1 FROM dbo.analytical_cohort WHERE cohort_id = ?",
            existence_params=(prepared.cohort_id,),
            insert_sql="""
                INSERT INTO dbo.analytical_cohort
                    (
                        cohort_id, source_id, name, selection_dimension,
                        provider_concept_id, definition_note
                    )
                VALUES (?, ?, ?, ?, ?, ?)
            """,
            insert_params=(
                prepared.cohort_id,
                source_id,
                ANALYTICAL_COHORT_NAME,
                "occupation_group",
                SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID,
                (
                    "Current first-slice analytical cohort. Data/IT remains the broader "
                    "acquisition boundary; individual occupation names are retained for audit "
                    "and are not used as a narrower whitelist."
                ),
            ),
        )

        _insert_if_missing(
            cursor,
            existence_sql="SELECT 1 FROM dbo.transformation WHERE transformation_id = ?",
            existence_params=(prepared.transformation_id,),
            insert_sql="""
                INSERT INTO dbo.transformation
                    (transformation_id, name, code_version, description)
                VALUES (?, ?, ?, ?)
            """,
            insert_params=(
                prepared.transformation_id,
                "Deterministic JobStream experience-signal audit",
                EXPERIENCE_AUDIT_VERSION,
                (
                    "Regex-based, inspectable audit separating quantified experience, "
                    "qualitative experience, meritorious experience and constrained seniority "
                    "language. Absence of a signal remains unknown."
                ),
            ),
        )

        for ad in prepared.ads:
            observed_at_expr = "CAST(? AS datetimeoffset(7))" if ad.observed_at else "NULL"
            insert_sql = f"""
                INSERT INTO dbo.evidence_item
                    (
                        evidence_item_id, source_id, batch_id, source_record_id,
                        observed_at, retrieved_at, raw_fingerprint, raw_location,
                        is_synthetic_test, generated_by_ai
                    )
                VALUES (
                    ?, ?, ?, ?,
                    {observed_at_expr},
                    CAST(? AS datetimeoffset(7)),
                    ?, ?, 0, 0
                )
            """
            item_params: tuple[Any, ...]
            if ad.observed_at:
                item_params = (
                    ad.evidence_item_id,
                    source_id,
                    str(manifest["batch_id"]),
                    ad.source_record_id,
                    ad.observed_at,
                    str(manifest["retrieved_at"]),
                    ad.raw_fingerprint,
                    ad.raw_location,
                )
            else:
                item_params = (
                    ad.evidence_item_id,
                    source_id,
                    str(manifest["batch_id"]),
                    ad.source_record_id,
                    str(manifest["retrieved_at"]),
                    ad.raw_fingerprint,
                    ad.raw_location,
                )

            _insert_if_missing(
                cursor,
                existence_sql="SELECT 1 FROM dbo.evidence_item WHERE evidence_item_id = ?",
                existence_params=(ad.evidence_item_id,),
                insert_sql=insert_sql,
                insert_params=item_params,
            )

            _insert_if_missing(
                cursor,
                existence_sql=(
                    "SELECT 1 FROM dbo.job_ad_observation WHERE evidence_item_id = ?"
                ),
                existence_params=(ad.evidence_item_id,),
                insert_sql="""
                    INSERT INTO dbo.job_ad_observation
                        (
                            evidence_item_id, headline,
                            occupation_concept_id, occupation_label,
                            occupation_group_concept_id, occupation_group_label,
                            occupation_field_concept_id, occupation_field_label,
                            provider_experience_required,
                            cohort_id, is_in_analytical_cohort,
                            experience_signal_status,
                            experience_audit_transformation_id
                        )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                insert_params=(
                    ad.evidence_item_id,
                    ad.headline,
                    ad.occupation_concept_id,
                    ad.occupation_label,
                    ad.occupation_group_concept_id,
                    ad.occupation_group_label,
                    ad.occupation_field_concept_id,
                    ad.occupation_field_label,
                    ad.provider_experience_required,
                    prepared.cohort_id,
                    ad.is_in_analytical_cohort,
                    ad.experience_signal_status,
                    prepared.transformation_id if ad.is_in_analytical_cohort else None,
                ),
            )

            if not ad.is_in_analytical_cohort:
                continue

            _insert_if_missing(
                cursor,
                existence_sql="""
                    SELECT 1
                    FROM dbo.transformation_input
                    WHERE transformation_id = ? AND evidence_item_id = ?
                """,
                existence_params=(prepared.transformation_id, ad.evidence_item_id),
                insert_sql="""
                    INSERT INTO dbo.transformation_input
                        (transformation_id, evidence_item_id)
                    VALUES (?, ?)
                """,
                insert_params=(prepared.transformation_id, ad.evidence_item_id),
            )

            for ordinal, signal in enumerate(ad.signals, start=1):
                _insert_if_missing(
                    cursor,
                    existence_sql="""
                        SELECT 1
                        FROM dbo.job_ad_experience_signal
                        WHERE evidence_item_id = ? AND signal_ordinal = ?
                    """,
                    existence_params=(ad.evidence_item_id, ordinal),
                    insert_sql="""
                        INSERT INTO dbo.job_ad_experience_signal
                            (
                                evidence_item_id, signal_ordinal, category,
                                source_field, matched_text, snippet
                            )
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    insert_params=(
                        ad.evidence_item_id,
                        ordinal,
                        signal["category"],
                        signal["source_field"],
                        signal["matched_text"],
                        signal["snippet"],
                    ),
                )

        batch_id = str(manifest["batch_id"])
        full_ads = int(
            cursor.execute(
                "SELECT COUNT(*) FROM dbo.evidence_item WHERE batch_id = ?",
                batch_id,
            ).fetchone()[0]
        )

        counts = cursor.execute(
            """
            SELECT
                SUM(CASE WHEN o.is_in_analytical_cohort = 1 THEN 1 ELSE 0 END),
                SUM(CASE WHEN o.is_in_analytical_cohort = 0 THEN 1 ELSE 0 END)
            FROM dbo.job_ad_observation o
            INNER JOIN dbo.evidence_item e
                ON e.evidence_item_id = o.evidence_item_id
            WHERE e.batch_id = ?
            """,
            batch_id,
        ).fetchone()
        cohort_ads = int(counts[0] or 0)
        out_of_cohort_ads = int(counts[1] or 0)

        transformation_inputs = int(
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM dbo.transformation_input
                WHERE transformation_id = ?
                """,
                prepared.transformation_id,
            ).fetchone()[0]
        )

        persisted_signals = int(
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM dbo.job_ad_experience_signal s
                INNER JOIN dbo.evidence_item e
                    ON e.evidence_item_id = s.evidence_item_id
                WHERE e.batch_id = ?
                """,
                batch_id,
            ).fetchone()[0]
        )

        expected_full = len(prepared.ads)
        expected_cohort = prepared.in_cohort_count
        if full_ads != expected_full:
            raise ValueError(
                f"post-load full-ad count mismatch: expected={expected_full} actual={full_ads}"
            )
        if cohort_ads != expected_cohort:
            raise ValueError(
                f"post-load cohort count mismatch: expected={expected_cohort} actual={cohort_ads}"
            )
        if out_of_cohort_ads != expected_full - expected_cohort:
            raise ValueError("post-load out-of-cohort count mismatch")
        if transformation_inputs != expected_cohort:
            raise ValueError("post-load transformation-input count mismatch")

        connection.commit()
        return LoadReport(
            batch_id=batch_id,
            raw_records=int(manifest["record_count"]),
            full_ads=full_ads,
            cohort_ads=cohort_ads,
            out_of_cohort_ads=out_of_cohort_ads,
            transformation_inputs=transformation_inputs,
            persisted_signals=persisted_signals,
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def persist_jobstream_manifest_to_sqlserver(
    manifest_path: Path,
    *,
    server: str = "localhost",
    database: str = "EventsToEvidence_Dev",
    driver: str = "ODBC Driver 18 for SQL Server",
) -> LoadReport:
    prepared = prepare_jobstream_batch(manifest_path)

    try:
        import pyodbc
    except ImportError as exc:
        raise RuntimeError(
            'pyodbc is required for SQL Server persistence; run pip install -e ".[dev]"'
        ) from exc

    connection_string = build_sqlserver_connection_string(
        server=server,
        database=database,
        driver=driver,
    )
    connection = pyodbc.connect(connection_string, autocommit=False)
    try:
        return load_prepared_jobstream_batch(connection, prepared)
    finally:
        connection.close()
