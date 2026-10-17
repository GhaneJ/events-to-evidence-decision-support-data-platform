import json

from evidence_intelligence.profiling.job_ads import profile_job_ads_jsonl


def test_profile_measures_first_slice_field_coverage(tmp_path) -> None:
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
                "must_have": {"skills": [], "work_experiences": []},
            },
        },
    ]
    path = tmp_path / "batch.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    report = profile_job_ads_jsonl(path)
    values = report.as_dict()

    assert values["records"] == 2
    assert values["records_with_ad_id"] == 2
    assert values["experience_required_present"] == 1
    assert values["must_have_work_experiences_present"] == 1
    assert values["must_have_experience_level_present"] == 1
    assert values["occupation_field_present_pct"] == 50.0
