import json

from evidence_intelligence.profiling.job_ads import profile_job_ads_jsonl


def test_profile_uses_full_ads_for_content_field_coverage(tmp_path) -> None:
    rows = [
        {
            "id": "a1",
            "experience_required": True,
            "occupation_field": {"concept_id": "data-it"},
            "publication_date": "2026-10-17T08:00:00",
            "description": {"text": "Backend role"},
            "must_have": {
                "skills": [{"concept_id": "python"}],
                "work_experiences": [
                    {"concept_id": "developer", "experience_level": {"label": "<1 year"}}
                ],
            },
        },
        {
            "event": "updated",
            "ad": {
                "id": "a2",
                "occupation_field": {"concept_id": "data-it"},
                "must_have": {"skills": [], "work_experiences": []},
            },
        },
        {
            "id": "a3",
            "removed": True,
            "removed_date": "2026-10-17T09:00:00",
            "occupation_field": {"concept_id": "data-it"},
        },
    ]
    path = tmp_path / "batch.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    values = profile_job_ads_jsonl(path).as_dict()

    assert values["records"] == 3
    assert values["removed_records"] == 1
    assert values["full_ad_records"] == 2
    assert values["records_with_ad_id"] == 3
    assert values["experience_required_present"] == 1
    assert values["experience_required_present_pct"] == 50.0
    assert values["must_have_work_experiences_present_pct"] == 50.0
    assert values["must_have_experience_level_present_pct"] == 50.0
    assert values["occupation_field_present_pct"] == 100.0


def test_profile_handles_removal_only_batch(tmp_path) -> None:
    row = {
        "id": "a1",
        "removed": True,
        "removed_date": "2026-10-17T09:00:00",
        "occupation_field": {"concept_id": "data-it"},
    }
    path = tmp_path / "batch.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    values = profile_job_ads_jsonl(path).as_dict()

    assert values["records"] == 1
    assert values["removed_records"] == 1
    assert values["full_ad_records"] == 0
    assert values["experience_required_present_pct"] == 0.0
    assert values["description_text_present_pct"] == 0.0
