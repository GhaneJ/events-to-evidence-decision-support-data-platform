from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class JobAdCoverageReport:
    records: int
    removed_records: int
    full_ad_records: int
    records_with_ad_id: int
    experience_required_present: int
    must_have_work_experiences_present: int
    must_have_experience_level_present: int
    must_have_skills_present: int
    occupation_field_present: int
    publication_date_present: int
    description_text_present: int

    def as_dict(self) -> dict[str, int | float]:
        result: dict[str, int | float] = asdict(self)
        stream_denominator = self.records or 1
        full_ad_denominator = self.full_ad_records or 1

        for key in (
            "removed_records",
            "full_ad_records",
            "records_with_ad_id",
            "occupation_field_present",
        ):
            result[f"{key}_pct"] = round(int(result[key]) * 100 / stream_denominator, 2)

        for key in (
            "experience_required_present",
            "must_have_work_experiences_present",
            "must_have_experience_level_present",
            "must_have_skills_present",
            "publication_date_present",
            "description_text_present",
        ):
            result[f"{key}_pct"] = round(int(result[key]) * 100 / full_ad_denominator, 2)

        return result


def _ad_payload(record: dict[str, Any]) -> dict[str, Any]:
    """Return the ad body from either a direct ad or a stream-event wrapper."""
    for key in ("ad", "data", "payload"):
        value = record.get(key)
        if isinstance(value, dict):
            return value
    return record


def _has_experience_level(work_experiences: object) -> bool:
    if not isinstance(work_experiences, list):
        return False
    for item in work_experiences:
        if not isinstance(item, dict):
            continue
        if item.get("experience_level") or item.get("erfarenhetsniva"):
            return True
    return False


def profile_job_ads_jsonl(path: Path) -> JobAdCoverageReport:
    counters = {
        "records": 0,
        "removed_records": 0,
        "full_ad_records": 0,
        "records_with_ad_id": 0,
        "experience_required_present": 0,
        "must_have_work_experiences_present": 0,
        "must_have_experience_level_present": 0,
        "must_have_skills_present": 0,
        "occupation_field_present": 0,
        "publication_date_present": 0,
        "description_text_present": 0,
    }

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue

            record = json.loads(raw_line)
            if not isinstance(record, dict):
                continue

            counters["records"] += 1
            ad = _ad_payload(record)
            is_removed = record.get("removed") is True or ad.get("removed") is True

            if is_removed:
                counters["removed_records"] += 1
            else:
                counters["full_ad_records"] += 1

            if ad.get("id"):
                counters["records_with_ad_id"] += 1
            if isinstance(ad.get("occupation_field"), dict):
                counters["occupation_field_present"] += 1

            if is_removed:
                continue

            if "experience_required" in ad and ad.get("experience_required") is not None:
                counters["experience_required_present"] += 1

            must_have = ad.get("must_have")
            if isinstance(must_have, dict):
                work_experiences = must_have.get("work_experiences")
                if isinstance(work_experiences, list) and work_experiences:
                    counters["must_have_work_experiences_present"] += 1
                    if _has_experience_level(work_experiences):
                        counters["must_have_experience_level_present"] += 1

                skills = must_have.get("skills")
                if isinstance(skills, list) and skills:
                    counters["must_have_skills_present"] += 1

            if ad.get("publication_date"):
                counters["publication_date_present"] += 1

            description = ad.get("description")
            if isinstance(description, dict) and description.get("text"):
                counters["description_text_present"] += 1

    return JobAdCoverageReport(**counters)
