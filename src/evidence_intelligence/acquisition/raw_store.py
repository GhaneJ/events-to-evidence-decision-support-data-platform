from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class RawBatchManifest:
    batch_id: str
    source_id: str
    endpoint: str
    retrieved_at: str
    request_parameters: Mapping[str, Any]
    record_count: int
    raw_sha256: str
    data_file: str


def land_ndjson_batch(
    lines: Iterable[str],
    *,
    output_dir: Path,
    source_id: str,
    endpoint: str,
    request_parameters: Mapping[str, Any],
    retrieved_at: datetime | None = None,
) -> RawBatchManifest:
    """Persist a JobStream response without changing individual JSON records.

    Each non-empty line is validated as JSON but written as supplied (apart from
    one normalized trailing newline).  The file-level SHA-256 makes the landed
    batch reproducible and tamper-evident before normalization begins.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = retrieved_at or datetime.now(UTC)
    batch_id = f"af-jobstream-{retrieved_at:%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    data_path = output_dir / f"{batch_id}.jsonl"
    manifest_path = output_dir / f"{batch_id}.manifest.json"

    digest = hashlib.sha256()
    record_count = 0

    with data_path.open("wb") as handle:
        for line in lines:
            normalized = line.rstrip("\r\n")
            if not normalized.strip():
                continue
            # Fail fast if the provider response is not valid NDJSON.
            json.loads(normalized)
            payload = (normalized + "\n").encode("utf-8")
            handle.write(payload)
            digest.update(payload)
            record_count += 1

    manifest = RawBatchManifest(
        batch_id=batch_id,
        source_id=source_id,
        endpoint=endpoint,
        retrieved_at=retrieved_at.isoformat(),
        request_parameters=dict(request_parameters),
        record_count=record_count,
        raw_sha256=digest.hexdigest(),
        data_file=data_path.name,
    )

    manifest_path.write_text(
        json.dumps(asdict(manifest), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
