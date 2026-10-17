# Events-to-Evidence Decision-Support Data Platform

A real-world data platform that brings together current and historical events, reports and observations from multiple sources, validates and cross-checks them while preserving their origin, and turns them into concise, traceable assessments for decision-makers. It helps decision-makers identify important patterns, see which findings are backed by consistent evidence, which findings remain uncertain, and where the evidence conflicts, and judge whether something should change, be investigated further, or remain as it is. AI helps interpret the question, find relevant sources and organize the information. Historical data is also used to detect recurring patterns and, when the evidence is strong enough, anticipate future trends or risks.

**Current implementation:** the first vertical slice investigates Swedish software/Data-IT entry accessibility. The description above defines the target system; it does not claim that every capability is implemented already. AI is an orchestrator/support role, not an evidence authority, and anticipation is added only when the historical data and evidence justify it.

**Start here:** read `PROJECT_REFERENCE.md`. It is the canonical living project state and anti-drift reference.

## Development

```bash
python -m venv .venv
# activate the environment
pip install -e ".[dev]"
pytest
```

## First real source-path commands

Land a bounded Data/IT JobStream window:

```bash
evidence-intel jobstream-ingest \
  --updated-after 2026-10-17T10:00:00 \
  --updated-before 2026-10-17T11:00:00
```

Profile the resulting raw JSONL file:

```bash
evidence-intel profile-job-ads data/raw/arbetsformedlingen/<batch>.jsonl
```

Do not add additional sources or presentation layers until the first source path is validated as described in `PROJECT_REFERENCE.md`.
