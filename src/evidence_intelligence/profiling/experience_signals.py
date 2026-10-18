from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID = "DJh5_yyF_hEM"

_NUMBER = (
    r"(?:\d{1,2}|en|ett|två|tre|fyra|fem|sex|sju|åtta|nio|tio|"
    r"one|two|three|four|five|six|seven|eight|nine|ten)"
)
_RANGE = rf"{_NUMBER}(?:\s*(?:[-–—]|till|to)\s*{_NUMBER})?"

_QUANTIFIED_EXPERIENCE = re.compile(
    rf"(?:\b{_RANGE}\s*(?:års?|years?)\b.{{0,45}}"
    rf"\b(?:erfarenhet|experience|arbete|work)\b|"
    rf"\b(?:erfarenhet|experience)\b.{{0,45}}\b{_RANGE}\s*(?:år|years?)\b)",
    re.IGNORECASE,
)

_QUALITATIVE_EXPERIENCE = re.compile(
    r"\b(?:"
    r"tidigare\s+erfarenhet|dokumenterad\s+erfarenhet|gedigen\s+erfarenhet|"
    r"god(?:a)?\s+(?:kunskaper\s+och\s+)?erfarenhet|praktisk\s+erfarenhet|"
    r"arbetslivserfarenhet|erfarenhet\s+(?:av|som|inom)|"
    r"previous\s+experience|prior\s+experience|professional\s+experience|"
    r"project\s+experience|hands-on\s+experience|"
    r"experience\s+(?:in|with|of|as)"
    r")\b",
    re.IGNORECASE,
)

_HEADLINE_SENIORITY = re.compile(r"\b(?:senior|lead|principal)\b", re.IGNORECASE)

_DESCRIPTION_SENIORITY = re.compile(
    r"\b(?:"
    r"(?:söker|seeking|looking\s+for)\s+(?:en|a|an)?\s*senior|"
    r"senior(?:a)?\s+(?:kompetensnivå|erfarenhet|kompetens)|"
    r"kompetensnivå\s*[3-5]"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ExperienceSignal:
    category: str
    source_field: str
    matched_text: str
    snippet: str


@dataclass(frozen=True, slots=True)
class JobExperienceAudit:
    ad_id: str | None
    headline: str | None
    occupation_concept_id: str | None
    occupation_label: str | None
    occupation_group_concept_id: str | None
    provider_experience_required: bool | None
    signals: tuple[ExperienceSignal, ...]

    @property
    def status(self) -> str:
        categories = {signal.category for signal in self.signals}
        if "quantified_experience" in categories or "seniority_language" in categories:
            return "explicit_threshold_or_seniority"
        if "qualitative_experience" in categories:
            return "qualitative_experience_only"
        if "meritorious_experience" in categories:
            return "meritorious_experience_only"
        return "unknown"

    def as_dict(self) -> dict[str, Any]:
        return {
            "ad_id": self.ad_id,
            "headline": self.headline,
            "occupation_concept_id": self.occupation_concept_id,
            "occupation_label": self.occupation_label,
            "occupation_group_concept_id": self.occupation_group_concept_id,
            "provider_experience_required": self.provider_experience_required,
            "status": self.status,
            "signals": [asdict(signal) for signal in self.signals],
        }


@dataclass(frozen=True, slots=True)
class ExperienceAuditReport:
    records: int
    removed_records: int
    full_ad_records: int
    cohort_records: int
    out_of_cohort_records: int
    ads: tuple[JobExperienceAudit, ...]

    def as_dict(self) -> dict[str, Any]:
        threshold_or_seniority = sum(
            ad.status == "explicit_threshold_or_seniority" for ad in self.ads
        )
        qualitative_only = sum(
            ad.status == "qualitative_experience_only" for ad in self.ads
        )
        meritorious_only = sum(
            ad.status == "meritorious_experience_only" for ad in self.ads
        )
        unknown = sum(ad.status == "unknown" for ad in self.ads)
        return {
            "records": self.records,
            "removed_records": self.removed_records,
            "full_ad_records": self.full_ad_records,
            "cohort_records": self.cohort_records,
            "out_of_cohort_records": self.out_of_cohort_records,
            "ads_with_explicit_threshold_or_seniority": threshold_or_seniority,
            "ads_with_qualitative_experience_only": qualitative_only,
            "ads_with_meritorious_experience_only": meritorious_only,
            "ads_with_unknown_experience_signal": unknown,
            "ads": [ad.as_dict() for ad in self.ads],
        }


def _ad_payload(record: dict[str, Any]) -> dict[str, Any]:
    for key in ("ad", "data", "payload"):
        value = record.get(key)
        if isinstance(value, dict):
            return value
    return record


def _concept_id(value: object) -> str | None:
    if isinstance(value, dict):
        concept_id = value.get("concept_id")
        if isinstance(concept_id, str):
            return concept_id
    return None


def _label(value: object) -> str | None:
    if isinstance(value, dict):
        label = value.get("label")
        if isinstance(label, str):
            return label
    return None


def _snippet(text: str, start: int, end: int, radius: int = 90) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return " ".join(text[left:right].split())


def _matches(
    text: str,
    pattern: re.Pattern[str],
    *,
    category: str,
    source_field: str,
) -> list[ExperienceSignal]:
    result: list[ExperienceSignal] = []
    for match in pattern.finditer(text):
        result.append(
            ExperienceSignal(
                category=category,
                source_field=source_field,
                matched_text=match.group(0),
                snippet=_snippet(text, match.start(), match.end()),
            )
        )
    return result


def _qualitative_matches(text: str, *, source_field: str) -> list[ExperienceSignal]:
    result: list[ExperienceSignal] = []
    for match in _QUALITATIVE_EXPERIENCE.finditer(text):
        prefix = text[max(0, match.start() - 220):match.start()]

        if re.search(
            r"\b(?:beskriv|describe)\s+(?:gärna\s+)?(?:kort\s+)?(?:din|your)?\s*$",
            prefix,
            re.IGNORECASE,
        ):
            continue

        category = "qualitative_experience"
        meritorious = re.search(
            r"\b(?:meriterande|preferred|desirable|nice\s+to\s+have)\b",
            prefix,
            re.IGNORECASE,
        )
        if meritorious:
            after_marker = prefix[meritorious.end():]
            mandatory_reset = re.search(
                r"(?:^|[.!?]\s+)(?:krav|requirements?|vi\s+söker|we\s+(?:seek|are\s+looking))\b",
                after_marker,
                re.IGNORECASE,
            )
            if not mandatory_reset:
                category = "meritorious_experience"

        result.append(
            ExperienceSignal(
                category=category,
                source_field=source_field,
                matched_text=match.group(0),
                snippet=_snippet(text, match.start(), match.end()),
            )
        )
    return result


def _signals_for_ad(ad: dict[str, Any]) -> tuple[ExperienceSignal, ...]:
    headline = ad.get("headline")
    description = ad.get("description")

    headline_text = headline if isinstance(headline, str) else ""
    description_text = ""
    if isinstance(description, dict):
        value = description.get("text")
        if isinstance(value, str):
            description_text = value

    signals: list[ExperienceSignal] = []

    for source_field, text in (
        ("headline", headline_text),
        ("description.text", description_text),
    ):
        signals.extend(
            _matches(
                text,
                _QUANTIFIED_EXPERIENCE,
                category="quantified_experience",
                source_field=source_field,
            )
        )
        signals.extend(
            _qualitative_matches(
                text,
                source_field=source_field,
            )
        )

    signals.extend(
        _matches(
            headline_text,
            _HEADLINE_SENIORITY,
            category="seniority_language",
            source_field="headline",
        )
    )
    signals.extend(
        _matches(
            description_text,
            _DESCRIPTION_SENIORITY,
            category="seniority_language",
            source_field="description.text",
        )
    )

    deduplicated: list[ExperienceSignal] = []
    seen: set[tuple[str, str, str, str]] = set()
    for signal in signals:
        key = (
            signal.category,
            signal.source_field,
            signal.matched_text.casefold(),
            signal.snippet.casefold(),
        )
        if key not in seen:
            seen.add(key)
            deduplicated.append(signal)

    return tuple(deduplicated)


def audit_experience_signals_jsonl(
    path: Path,
    *,
    occupation_group_id: str = SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID,
) -> ExperienceAuditReport:
    records = 0
    removed_records = 0
    full_ad_records = 0
    out_of_cohort_records = 0
    ads: list[JobExperienceAudit] = []

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue

            record = json.loads(raw_line)
            if not isinstance(record, dict):
                continue

            records += 1
            ad = _ad_payload(record)
            is_removed = record.get("removed") is True or ad.get("removed") is True
            if is_removed:
                removed_records += 1
                continue

            full_ad_records += 1
            occupation_group = ad.get("occupation_group")
            group_id = _concept_id(occupation_group)
            if group_id != occupation_group_id:
                out_of_cohort_records += 1
                continue

            occupation = ad.get("occupation")
            provider_value = ad.get("experience_required")
            provider_experience_required = provider_value if isinstance(provider_value, bool) else None

            ad_id = ad.get("id")
            headline = ad.get("headline")
            ads.append(
                JobExperienceAudit(
                    ad_id=ad_id if isinstance(ad_id, str) else None,
                    headline=headline if isinstance(headline, str) else None,
                    occupation_concept_id=_concept_id(occupation),
                    occupation_label=_label(occupation),
                    occupation_group_concept_id=group_id,
                    provider_experience_required=provider_experience_required,
                    signals=_signals_for_ad(ad),
                )
            )

    return ExperienceAuditReport(
        records=records,
        removed_records=removed_records,
        full_ad_records=full_ad_records,
        cohort_records=len(ads),
        out_of_cohort_records=out_of_cohort_records,
        ads=tuple(ads),
    )
