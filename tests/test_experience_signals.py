import json

from evidence_intelligence.profiling.experience_signals import (
    SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID,
    audit_experience_signals_jsonl,
)


def _write(tmp_path, rows):
    path = tmp_path / "batch.jsonl"
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def test_audit_filters_removals_and_out_of_cohort_records(tmp_path) -> None:
    rows = [
        {
            "id": "in-1",
            "headline": "DevOps Engineer",
            "occupation_group": {
                "concept_id": SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID,
                "label": "Mjukvaru- och systemutvecklare m.fl.",
            },
            "experience_required": True,
            "description": {"text": "Minst fyra års erfarenhet som DevOps Engineer."},
        },
        {
            "id": "out-1",
            "headline": "Supporttekniker",
            "occupation_group": {"concept_id": "other"},
            "description": {"text": "Två års erfarenhet av support."},
        },
        {
            "id": "removed-1",
            "removed": True,
            "occupation_group": {"concept_id": SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID},
        },
    ]

    values = audit_experience_signals_jsonl(_write(tmp_path, rows)).as_dict()

    assert values["records"] == 3
    assert values["removed_records"] == 1
    assert values["full_ad_records"] == 2
    assert values["cohort_records"] == 1
    assert values["out_of_cohort_records"] == 1
    assert values["ads_with_explicit_threshold_or_seniority"] == 1
    assert values["ads"][0]["provider_experience_required"] is True


def test_audit_preserves_inspectable_quantified_and_seniority_signals(tmp_path) -> None:
    rows = [
        {
            "id": "a1",
            "headline": "Senior Data Engineer",
            "occupation": {"concept_id": "dw", "label": "Data Warehouse specialist"},
            "occupation_group": {"concept_id": SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID},
            "experience_required": True,
            "description": {
                "text": (
                    "Uppdraget avser senior kompetensnivå 3, som normalt uppnås "
                    "tidigast efter 9–12 års arbete inom området."
                )
            },
        }
    ]

    ad = audit_experience_signals_jsonl(_write(tmp_path, rows)).as_dict()["ads"][0]

    assert ad["status"] == "explicit_threshold_or_seniority"
    categories = {signal["category"] for signal in ad["signals"]}
    assert "quantified_experience" in categories
    assert "seniority_language" in categories
    assert any("9–12 års arbete" in signal["matched_text"] for signal in ad["signals"])
    assert all(signal["snippet"] for signal in ad["signals"])


def test_qualitative_experience_is_not_promoted_to_threshold(tmp_path) -> None:
    rows = [
        {
            "id": "a1",
            "headline": "Webbutvecklare",
            "occupation_group": {"concept_id": SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID},
            "experience_required": True,
            "description": {"text": "Erfarenhet av Node.js."},
        }
    ]

    values = audit_experience_signals_jsonl(_write(tmp_path, rows)).as_dict()
    ad = values["ads"][0]

    assert ad["status"] == "qualitative_experience_only"
    assert values["ads_with_qualitative_experience_only"] == 1
    assert values["ads_with_explicit_threshold_or_seniority"] == 0


def test_meritorious_experience_is_kept_separate_from_requirement(tmp_path) -> None:
    rows = [
        {
            "id": "a1",
            "headline": "Systemutvecklare",
            "occupation_group": {"concept_id": SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID},
            "description": {"text": "Meriterande Erfarenhet av Databricks."},
        }
    ]

    values = audit_experience_signals_jsonl(_write(tmp_path, rows)).as_dict()
    ad = values["ads"][0]

    assert ad["status"] == "meritorious_experience_only"
    assert values["ads_with_meritorious_experience_only"] == 1
    assert ad["signals"][0]["category"] == "meritorious_experience"


def test_meritorious_context_can_cover_consecutive_experience_sentences(tmp_path) -> None:
    rows = [
        {
            "id": "a1",
            "headline": "Data Engineer",
            "occupation_group": {"concept_id": SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID},
            "description": {
                "text": (
                    "Meriterande Erfarenhet av Databricks, Microsoft Fabric eller liknande "
                    "moderna dataplattformar. Erfarenhet av C# och Python. Som person är du analytisk."
                )
            },
        }
    ]

    values = audit_experience_signals_jsonl(_write(tmp_path, rows)).as_dict()
    ad = values["ads"][0]

    assert ad["status"] == "meritorious_experience_only"
    assert len(ad["signals"]) == 2
    assert all(signal["category"] == "meritorious_experience" for signal in ad["signals"])


def test_application_instruction_is_not_experience_evidence(tmp_path) -> None:
    rows = [
        {
            "id": "a1",
            "headline": "Systemutvecklare",
            "occupation_group": {"concept_id": SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID},
            "description": {
                "text": "Beskriv gärna kort din erfarenhet av relevanta dataplattformar i ansökan."
            },
        }
    ]

    values = audit_experience_signals_jsonl(_write(tmp_path, rows)).as_dict()
    ad = values["ads"][0]

    assert ad["status"] == "unknown"
    assert ad["signals"] == []


def test_audit_treats_no_detected_signal_as_unknown(tmp_path) -> None:
    rows = [
        {
            "id": "a1",
            "headline": "Systemutvecklare",
            "occupation_group": {"concept_id": SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID},
            "experience_required": True,
            "description": {"text": "Vi söker en utvecklare som vill arbeta med Python."},
        }
    ]

    values = audit_experience_signals_jsonl(_write(tmp_path, rows)).as_dict()

    assert values["ads_with_unknown_experience_signal"] == 1
    assert values["ads"][0]["status"] == "unknown"
    assert values["ads"][0]["signals"] == []


def test_senior_colleagues_do_not_mark_role_as_senior(tmp_path) -> None:
    rows = [
        {
            "id": "a1",
            "headline": "Projektledare IT",
            "occupation_group": {"concept_id": SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID},
            "description": {"text": "Du arbetar nära sponsorer och seniora beslutsfattare."},
        }
    ]

    ad = audit_experience_signals_jsonl(_write(tmp_path, rows)).as_dict()["ads"][0]

    assert not any(signal["category"] == "seniority_language" for signal in ad["signals"])
