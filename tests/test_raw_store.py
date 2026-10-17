import hashlib
import json
from datetime import UTC, datetime

import pytest

from evidence_intelligence.acquisition.raw_store import land_ndjson_batch


def test_raw_store_preserves_ndjson_and_manifest(tmp_path) -> None:
    lines = ['{"id":"a1","headline":"Data engineer"}', '{"id":"a2"}']
    retrieved = datetime(2026, 10, 17, 16, 0, tzinfo=UTC)

    manifest = land_ndjson_batch(
        lines,
        output_dir=tmp_path,
        source_id="af-jobstream-v2",
        endpoint="/v2/stream",
        request_parameters={"occupation_concept_ids": ["data-it"]},
        retrieved_at=retrieved,
    )

    data = (tmp_path / manifest.data_file).read_bytes()
    assert data == ("\n".join(lines) + "\n").encode()
    assert manifest.record_count == 2
    assert manifest.raw_sha256 == hashlib.sha256(data).hexdigest()

    manifest_files = list(tmp_path.glob("*.manifest.json"))
    assert len(manifest_files) == 1
    persisted = json.loads(manifest_files[0].read_text(encoding="utf-8"))
    assert persisted["batch_id"] == manifest.batch_id


def test_raw_store_rejects_invalid_json_line(tmp_path) -> None:
    with pytest.raises(json.JSONDecodeError):
        land_ndjson_batch(
            ["not-json"],
            output_dir=tmp_path,
            source_id="af",
            endpoint="/v2/stream",
            request_parameters={},
        )
