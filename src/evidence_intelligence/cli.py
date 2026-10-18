from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .acquisition.raw_store import land_ndjson_batch
from .profiling.experience_signals import (
    SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID,
    audit_experience_signals_jsonl,
)
from .profiling.job_ads import profile_job_ads_jsonl
from .persistence.evidence_statement_sqlserver import (
    persist_jobstream_experience_statement_sqlserver,
)
from .persistence.jobstream_sqlserver import persist_jobstream_manifest_to_sqlserver
from .sources.arbetsformedlingen import (
    DATA_IT_OCCUPATION_FIELD_CONCEPT_ID,
    JobSearchClient,
    JobStreamClient,
)


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use ISO-8601, e.g. 2026-10-17T12:00:00") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evidence-intel")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser(
        "jobstream-ingest",
        help="Land a bounded Arbetsförmedlingen JobStream v2 window as raw NDJSON",
    )
    ingest.add_argument("--updated-after", required=True, type=_parse_datetime)
    ingest.add_argument("--updated-before", type=_parse_datetime)
    ingest.add_argument(
        "--occupation-concept-id",
        action="append",
        default=None,
        help="Repeat for multiple occupation concepts; defaults to Data/IT for this slice",
    )
    ingest.add_argument("--output-dir", type=Path, default=Path("data/raw/arbetsformedlingen"))

    profile = sub.add_parser("profile-job-ads", help="Profile first-slice JobStream field coverage")
    profile.add_argument("path", type=Path)

    audit = sub.add_parser(
        "audit-experience-signals",
        help="Audit explicit text-derived experience signals in the current analytical cohort",
    )
    audit.add_argument("path", type=Path)
    audit.add_argument(
        "--occupation-group-id",
        default=SOFTWARE_DEVELOPMENT_OCCUPATION_GROUP_ID,
    )

    persist = sub.add_parser(
        "persist-jobstream-sqlserver",
        help="Persist one validated JobStream raw batch and lineage into SQL Server",
    )
    persist.add_argument("manifest", type=Path)
    persist.add_argument("--server", default="localhost")
    persist.add_argument("--database", default="EventsToEvidence_Dev")
    persist.add_argument("--driver", default="ODBC Driver 18 for SQL Server")

    statement = sub.add_parser(
        "persist-jobstream-statement-sqlserver",
        help="Persist the batch-bounded JobStream experience evidence statement",
    )
    statement.add_argument("batch_id")
    statement.add_argument("--server", default="localhost")
    statement.add_argument("--database", default="EventsToEvidence_Dev")
    statement.add_argument("--driver", default="ODBC Driver 18 for SQL Server")

    # Kept as an exploratory helper, not the ingestion boundary.
    jobsearch = sub.add_parser("jobsearch", help="Explore a small current JobSearch result")
    jobsearch.add_argument("query")
    jobsearch.add_argument("--limit", type=int, default=10)
    jobsearch.add_argument("--offset", type=int, default=0)
    jobsearch.add_argument("--occupation-field")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "jobstream-ingest":
        occupation_ids = tuple(args.occupation_concept_id or [DATA_IT_OCCUPATION_FIELD_CONCEPT_ID])
        request_parameters = {
            "updated_after": args.updated_after.isoformat(),
            "updated_before": args.updated_before.isoformat() if args.updated_before else None,
            "occupation_concept_ids": list(occupation_ids),
        }
        with JobStreamClient() as client:
            lines = client.iter_changes(
                args.updated_after,
                updated_before=args.updated_before,
                occupation_concept_ids=occupation_ids,
            )
            manifest = land_ndjson_batch(
                lines,
                output_dir=args.output_dir,
                source_id="arbetsformedlingen-jobstream-v2",
                endpoint="/v2/stream",
                request_parameters=request_parameters,
            )
        print(json.dumps(asdict(manifest), ensure_ascii=False, indent=2))
        return

    if args.command == "profile-job-ads":
        report = profile_job_ads_jsonl(args.path)
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return

    if args.command == "audit-experience-signals":
        report = audit_experience_signals_jsonl(
            args.path,
            occupation_group_id=args.occupation_group_id,
        )
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "persist-jobstream-sqlserver":
        report = persist_jobstream_manifest_to_sqlserver(
            args.manifest,
            server=args.server,
            database=args.database,
            driver=args.driver,
        )
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "persist-jobstream-statement-sqlserver":
        report = persist_jobstream_experience_statement_sqlserver(
            batch_id=args.batch_id,
            server=args.server,
            database=args.database,
            driver=args.driver,
        )
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "jobsearch":
        with JobSearchClient() as client:
            payload = client.search(
                args.query,
                limit=args.limit,
                offset=args.offset,
                occupation_field=args.occupation_field,
            )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
