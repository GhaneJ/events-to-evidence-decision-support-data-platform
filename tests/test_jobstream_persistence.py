import hashlib
import json

import pytest

from evidence_intelligence.persistence.jobstream_sqlserver import (
    build_sqlserver_connection_string,
    prepare_jobstream_batch,
)
from evidence_intelligence.profiling.experience_signals import (
    SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID,
)


def _write_batch(tmp_path):
    rows = [
        {
            "id": "a1",
            "headline": "Senior Data Engineer",
            "publication_date": "2026-10-17T08:00:00+00:00",
            "occupation": {"concept_id": "dw", "label": "Data Warehouse specialist"},
            "occupation_group": {
                "concept_id": SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID,
                "label": "Mjukvaru- och systemutvecklare m.fl.",
            },
            "occupation_field": {"concept_id": "data-it", "label": "Data/IT"},
            "experience_required": True,
            "description": {"text": "Minst fyra års erfarenhet som Data Engineer."},
        },
        {
            "id": "a2",
            "headline": "Supporttekniker",
            "publication_date": "2026-10-17T09:00:00+00:00",
            "occupation_group": {"concept_id": "other", "label": "Other"},
            "occupation_field": {"concept_id": "data-it", "label": "Data/IT"},
            "experience_required": True,
            "description": {"text": "Två års erfarenhet av support."},
        },
        {
            "id": "a3",
            "removed": True,
            "removed_date": "2026-10-17T10:00:00+00:00",
        },
    ]
    data_path = tmp_path / "batch.jsonl"
    raw = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode()
    data_path.write_bytes(raw)

    manifest = {
        "batch_id": "af-jobstream-test",
        "source_id": "arbetsformedlingen-jobstream-v2",
        "endpoint": "/v2/stream",
        "retrieved_at": "2026-10-18T09:24:02+00:00",
        "request_parameters": {"occupation_concept_ids": ["data-it"]},
        "record_count": 3,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "data_file": data_path.name,
    }
    manifest_path = tmp_path / "batch.manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, data_path


def test_prepare_batch_preserves_lineage_and_cohort_semantics(tmp_path) -> None:
    manifest_path, _ = _write_batch(tmp_path)

    prepared = prepare_jobstream_batch(manifest_path)

    assert len(prepared.ads) == 2
    assert prepared.in_cohort_count == 1

    in_cohort = next(ad for ad in prepared.ads if ad.source_record_id == "a1")
    assert in_cohort.is_in_analytical_cohort is True
    assert in_cohort.provider_experience_required is True
    assert in_cohort.experience_signal_status == "explicit_threshold_or_seniority"
    assert in_cohort.raw_location.endswith("batch.jsonl#line=1")
    assert len(in_cohort.raw_fingerprint) == 64
    assert any(signal["category"] == "quantified_experience" for signal in in_cohort.signals)

    out_of_cohort = next(ad for ad in prepared.ads if ad.source_record_id == "a2")
    assert out_of_cohort.is_in_analytical_cohort is False
    assert out_of_cohort.experience_signal_status is None
    assert out_of_cohort.signals == ()


def test_prepare_batch_rejects_raw_tampering(tmp_path) -> None:
    manifest_path, data_path = _write_batch(tmp_path)
    data_path.write_text(
        data_path.read_text(encoding="utf-8") + '{"id":"extra"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        prepare_jobstream_batch(manifest_path)


def test_connection_string_uses_local_windows_authentication() -> None:
    value = build_sqlserver_connection_string(
        server="localhost",
        database="EventsToEvidence_Dev",
    )

    assert "ODBC Driver 18 for SQL Server" in value
    assert "Trusted_Connection=yes" in value
    assert "Encrypt=yes" in value
    assert "TrustServerCertificate=yes" in value
