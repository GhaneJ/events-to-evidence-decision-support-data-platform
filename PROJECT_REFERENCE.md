# Events-to-Evidence Decision-Support Data Platform — Project Reference

**Authority:** Canonical living implementation reference. Read this file before substantive design or coding. Historical baseline/checkpoint documents remain authoritative for the decisions they record; this file carries their current implementation state forward.

**Last synchronized:** 2026-10-18
**Current milestone:** First Candidate A vertical slice — first-source persistence and lineage
**Current implementation question:** *When aggregate software-development demand appears strong, is that demand actually accessible to newly qualified workers, or is a growing share concentrated among experienced or specialized candidates?*

## Public identity and target-system description

**Display name:** Events-to-Evidence Decision-Support Data Platform  
**Repository slug:** `events-to-evidence-decision-support-data-platform`

**Agreed public description:**

> A real-world data platform that brings together current and historical events, reports and observations from multiple sources, validates and cross-checks them while preserving their origin, and turns them into concise, traceable assessments for decision-makers. It helps decision-makers identify important patterns, see which findings are backed by consistent evidence, which findings remain uncertain, and where the evidence conflicts, and judge whether something should change, be investigated further, or remain as it is. AI helps interpret the question, find relevant sources and organize the information. Historical data is also used to detect recurring patterns and, when the evidence is strong enough, anticipate future trends or risks.

This description states the intended whole-system value, not a claim that every capability is already implemented. The current vertical slice remains the implementation truth. In particular, AI is an agreed orchestration role but no AI component is yet required by the current slice, and anticipation remains conditional on historical depth, data quality and evidential support.

In this description, **consistent evidence** means evidence that converges after provenance, independence/ancestry and counter-evidence checks. Multiple publications derived from the same underlying survey or dataset do not count as independent support.

The former working title **Evidence-Driven Event Intelligence Platform** remains in historical checkpoints only. Those documents are preserved as historical decision records; they do not override this living reference for current project identity or state.

## 1. Project purpose

Build the smallest complete, defensible real-world data platform that can bring together current and historical information from multiple sources, preserve provenance and evidence ancestry, transform it reproducibly, compare supporting and conflicting evidence, expose uncertainty, and produce concise, inspectable decision-support assessments.

The first implementation domain is Swedish Skills Mismatch / Labor-Market Intelligence, narrowed to software-development / Data-IT entry accessibility. The platform is not a generic dashboard, not a general-purpose chatbot, and not a commissioned product for a fictional customer.

## 2. Non-negotiable rules

1. **Reality before technology.** Real societal evidence is required; synthetic data may only be used for isolated technical tests and must never masquerade as societal evidence.
2. **Triangulation is a core pillar.** Consequential conclusions should be tested across genuinely independent evidence families where possible.
3. **Evidence ancestry matters more than publication count.** Republishing the same underlying survey or dataset does not create independent corroboration.
4. **Counter-evidence is mandatory.** The workflow must deliberately preserve evidence that weakens or competes with a favored explanation.
5. **Conclusions are calibrated.** Observed fact, statistical association, supported interpretation, hypothesis, contested explanation, or unresolved question.
6. **AI is not the authority.** Its agreed role is to help interpret bounded questions, find relevant sources, map/organize information and support the evidence workflow when implementation earns it. AI-generated prose is not evidence and cannot silently determine conclusions.
7. **Reduce breadth, not evidential depth.** One bounded question receives the full evidence discipline before the project expands.
8. **No architecture theater.** Every component must earn its place through a current requirement or acceptance criterion.
9. **Data Engineering first.** Languages and frameworks are implementation tools, not project goals. .NET/C# is added only if a real system requirement earns it; it is not inserted because of the developer's previous background.
10. **Human decision support only.** The platform informs decisions; it does not make official institutional decisions automatically.
11. **No significant project change is allowed to happen silently.**

## 3. Documentation-continuity rule

Documentation is part of the definition of done, not an after-action task.

A work step is **incomplete** when material code, data-source, model, scope, architecture, acceptance criteria, or decision state changes without updating this file in the same work cycle.

### Start-of-session check

- Read this file first.
- Confirm the current milestone, fixed decisions, provisional decisions, open risks, and exact next step before changing implementation.
- Do not reconstruct project state from chat memory when this file is available.

### End-of-session sync

Before work is considered complete, update only the sections affected by the work:

- Current milestone / current state
- Fixed or provisional decisions
- Data-source contracts and provenance assumptions
- Domain/data model when materially changed
- Acceptance criteria when materially changed
- Open risks or resolved risks
- Change history
- Exact next step

Do not create parallel governance documents that duplicate this file.

## 4. Scope gate

Before adding any feature, dataset, technology, dashboard, service, AI component, queue, graph, or deployment layer, answer:

> Which current requirement or acceptance criterion requires this now?

If there is no concrete answer, it stays out of the current slice.

## 5. First vertical slice

### Input

A bounded investigation question about entry accessibility in Swedish software-development / Data-IT demand.

### Minimum workflow

1. Load the bounded investigation question.
2. Identify required evidence families.
3. Acquire a deliberately small set of real public evidence.
4. Normalize only dimensions required by the question: time, occupation, geography, skills, and experience indicators where available.
5. Preserve raw source identity, retrieval time, evidence family, source record identity, and transformation lineage.
6. Produce explicit evidence statements, not free-form model opinions.
7. Compare support, conflict, gaps, and shared ancestry.
8. Classify the assessment using the agreed evidence vocabulary.
9. Produce a concise assessment with inspectable evidence and uncertainty.
10. Expose a downstream-ready decision artifact through the simplest interface actually required by the slice.

### Acceptance criterion

The slice succeeds when real public data produces one defensible assessment where a reader can inspect the source and lineage of every consequential statement, distinguish independent corroboration from shared ancestry, see relevant counter-evidence, and understand remaining uncertainty.

A data ingestion demo or dashboard alone does not satisfy this criterion.

## 6. Technology-selection gate

### 6.1 Historically agreed directions

These came from the earlier platform baseline and remain compatible with Candidate A:

| Boundary | Agreed direction | Current meaning |
|---|---|---|
| Pipeline / data processing | Python | Still valid and used in the first slice. |
| Persistent data | SQL-oriented storage | Still valid; exact product was historically open. |
| Downstream serving | API / serving boundary | Direction remains useful, but framework and timing are open. |
| Deployment | Containers only when useful | Still deferred until reproducibility/deployment needs earn them. |
| AI | Orchestration/support role, never evidence authority | Conceptual role agreed; implementation remains deferred until the slice earns it. |

The old C#/WPF choice belonged specifically to the parked Mafia source path and does **not** carry into Candidate A.

### 6.2 Provisional first-slice choices

These are deliberate engineering choices for the vertical slice, **not historical decisions and not automatically permanent whole-project architecture**:

| Boundary | First-slice choice | Why it earns a place | Status |
|---|---|---|---|
| Runtime | Python 3.12+ | Natural fit for acquisition, profiling, ETL/ELT and evidence processing; matches the agreed pipeline direction. | Provisional for slice |
| HTTP client | `httpx` | Small, testable client for official APIs; no framework commitment. | Implementation choice |
| Raw landing | Immutable NDJSON + manifest on local filesystem | Preserves source response before transformation, supports reproducibility and streaming without database coupling. | Provisional for slice |
| Relational persistence | Microsoft SQL Server | Satisfies the agreed SQL-oriented storage boundary with relational constraints, `DATETIMEOFFSET`, JSON validation through `ISJSON`, mature T-SQL tooling, and local-first operation. No current requirement depends on a database-specific capability unavailable in SQL Server. | First-slice decision |
| Automated tests | `pytest` | Lightweight, natural for Python source adapters and evidence rules. | Implementation choice |
| User interface / visualization | None yet | The evidence path must work before a UI earns its place. | Open / deferred |
| Serving API framework | None yet | A serving boundary is a direction, but no API framework is required by the current acquisition milestone. | Open / deferred |
| .NET / C# | None yet | Add only if a real serving/application requirement makes it the best fit. | Open / deferred |
| Cloud | None required | Local-first avoids cost and does not weaken the first-slice learning goals. | Deferred |
| Containers | None required yet | Add only if reproducibility/deployment materially benefits. | Deferred |
| AI component | None | The public target role is defined, but rules and engineered evidence come first. | Deferred |

### 6.3 Technology rule

Technology is selected because it improves the system, not because it showcases a résumé skill. The project is primarily a Data Engineering degree/portfolio project; architecture and logic take precedence over language identity.

## 7. Current source plan

### Source path 1 — Arbetsförmedlingen JobStream v2

**Primary ingestion boundary:** `https://jobstream.api.jobtechdev.se/v2/stream`  
**Format:** NDJSON (`Accept: application/jsonl`)  
**Purpose in slice:** observed job-ad changes and structured experience/skill signals.  
**Evidence family:** observed public job advertisements.  
**Current Data/IT occupation-field concept used by the slice:** `apaJ_2ja_LuF`.

Why JobStream rather than JobSearch: Arbetsförmedlingen's own guidance says JobStream should be used when keeping a local copy or ingesting all ads / a filtered market subset. JobSearch remains only an exploratory helper for small current searches.

The first ingestion uses a **bounded time window** and Data/IT occupation filter rather than downloading the full snapshot. This keeps the first slice small while exercising the correct ingestion contract.

JobStream `/v2/stream` contains both full advertisement events and sparse removal events. Removal events remain part of the immutable raw stream and provenance, but they must not be included in denominators for full-ad content-field completeness.

**Acquisition boundary vs analytical cohort:** the Data/IT occupation field `apaJ_2ja_LuF` remains the broad acquisition filter. For the current software-development question, the analytical cohort is the provider occupation group `DJh5_yyF_hEM` — **Mjukvaru- och systemutvecklare m.fl.** (2512). Ads in other Data/IT occupation groups remain in the raw evidence but are outside the current cohort. Individual occupation names are not whitelisted more narrowly at this stage because variation and specialization inside the group are part of the question being investigated; occupation and headline remain available for stratification and audit.

Important limitation: job advertisements are not the whole labor market and cannot independently prove employer shortage, graduate outcomes, or causality.

Official source-contract references:

- JobStream Swagger: https://jobstream.api.jobtechdev.se/swagger.json
- JobStream getting started: https://gitlab.com/arbetsformedlingen/job-ads/jobsearch-apis/-/blob/main/docs/GettingStartedJobStreamEN.md
- Ad fields: https://gitlab.com/arbetsformedlingen/job-ads/jobsearch/jobsearch-api/-/blob/main/docs/AdFields.md

### Later evidence families for triangulation

- MYH / SCB graduate outcomes
- SCB / Arbetsförmedlingen employer-side evidence, with shared ancestry recorded where applicable
- Regional indicators / outlooks
- Selected independent research where methodologically useful

These are not integrated in parallel before the first source path has been landed, profiled and persisted reproducibly.

## 8. Minimum domain model

- `InvestigationQuestion`
- `EvidenceFamily`
- `Source`
- `IngestionBatch`
- `EvidenceItem`
- `Transformation`
- `EvidenceStatement`
- `Assessment`
- `DecisionArtifact`

The persistence model is relational and normalized around provenance. Raw provider payloads remain outside the normalized model and are referenced by batch/file lineage.

## 9. Evidence rules implemented in the foundation

- AI-generated content cannot be instantiated as societal evidence.
- Synthetic technical-test evidence cannot support a real assessment.
- Every evidence statement must trace to one or more evidence items.
- Every assessment must record uncertainty.
- Counter-evidence search/check must be explicit before an assessment is considered valid.
- A `supported interpretation` requires at least two independent evidence families in the material currently supporting the assessment.
- Repeated items from one evidence family count as one family for corroboration.

These rules are intentionally stricter than presentation logic and may be refined only through a recorded project decision.

## 10. First source-path behavior now implemented

1. `JobStreamClient` calls current `/v2/stream` with bounded timestamps.
2. Data/IT is passed as an occupation concept filter rather than inferred from free text.
3. The client requests NDJSON so responses can be streamed without loading the whole batch into memory.
4. Raw NDJSON is landed locally without transforming source records.
5. A batch manifest records source, endpoint, request parameters, retrieval time, record count and SHA-256 fingerprint.
6. A field-coverage profiler separates full advertisements from sparse removal events and measures full-ad content fields against the full-ad denominator before we design the analytical rule.
7. JobSearch is retained only as an exploratory helper, not as the ingestion source.
8. A deterministic experience-signal audit filters the current analytical cohort and preserves matched text/snippets for quantified experience, qualitative experience, meritorious experience, and constrained seniority language. The audit separates explicit year-threshold/seniority evidence, qualitative requirement language, and merely meritorious experience; application instructions asking candidates to describe experience are excluded. None of these states is automatically translated into junior-friendliness, and no detected signal is reported as `unknown`.

## 11. Explicitly out of scope for the first build

- Universal labor-market simulation
- General-purpose chatbot
- Synthetic societal data used to fill evidence gaps
- Multiple candidate domains implemented in parallel
- Prediction/forecasting before descriptive and diagnostic integration is useful
- Automated institutional decisions
- Multi-agent architecture for sophistication
- Microservices, message brokers, vector databases, graph databases, or similar infrastructure without a demonstrated need
- Cloud deployment merely to demonstrate cloud usage
- .NET/C# merely to demonstrate prior developer experience
- Any dashboard/UI before the evidence path proves what must be shown

## 12. Current risks

1. Structured job-ad requirement fields are too sparse in the first real batch to support entry-accessibility measurement by themselves.
2. The provider documents `experience_required` as indicating that no experience is required, but the first real batch shows direct conflicts with advertisement text; it must not be used as a standalone accessibility indicator.
3. The semantics of `experience_required` and experience-level structures must be verified before analytical use; no conclusion is allowed from field names alone.
4. Occupation and education classifications may not align cleanly across later sources.
5. Shared evidence ancestry can create false confidence if not modeled explicitly.
6. The platform must avoid causal language when the evidence only supports association or competing explanations.
7. The build must demonstrate value beyond aggregation; conflict/ancestry analysis remains the first value hypothesis.
8. Scope growth remains a risk; the first implementation question stays fixed until the vertical slice is complete.

## 13. Current state

Foundation established on 2026-10-17; first live-source validation continued on 2026-10-18:

- Canonical living project reference established and synchronized.
- Documentation continuity is part of definition of done.
- Historical technology decisions separated from new provisional first-slice choices.
- Unsupported Power BI assumption removed; visualization remains open.
- .NET/C# explicitly remains optional and requirement-driven.
- Python domain model and evidence-validation rules retained.
- The relational foundation is targeted to Microsoft SQL Server and expressed as T-SQL in `sql/001_initial_schema.sql`.
- The core SQL Server schema has been validated successfully in the local `EventsToEvidence_Dev` database: 12 core user tables, 12 foreign keys, 7 check constraints and 2 intended explicit indexes.
- `sql/002_jobstream_source_persistence.sql` has been added and validated successfully, extending the model to 15 user tables, 17 foreign keys and 11 check constraints.
- The JobStream persistence extension adds `analytical_cohort`, `job_ad_observation` and `job_ad_experience_signal`. Batch lineage remains normalized through `evidence_item -> ingestion_batch`; raw provider payloads remain in immutable NDJSON rather than being duplicated into normalized tables.
- Primary Arbetsförmedlingen ingestion corrected from JobSearch to JobStream v2.
- NDJSON streaming client implemented with bounded time and occupation filters.
- Immutable raw landing + manifest fingerprint implemented.
- Job-ad field-coverage profiler implemented and corrected so sparse removal events do not dilute full-ad content coverage.
- First real 24-hour Data/IT JobStream batch contained 93 events: 77 removals and 16 full advertisements.
- In the 16 full advertisements, description text, publication date and `experience_required` were present in 16/16; structured `must_have.work_experiences` and `must_have.skills` were present in 1/16 each; structured experience level was present in 0/16.
- All 16 full advertisements had `experience_required = true`, while multiple advertisement texts explicitly demanded prior experience, including multi-year requirements and senior roles. The field is therefore retained as source data but rejected as a standalone entry-accessibility measure.
- The current analytical cohort is occupation group `DJh5_yyF_hEM` (`Mjukvaru- och systemutvecklare m.fl.`, 2512): 9 of the 16 full advertisements in the first batch. The remaining 7 ads stay in raw evidence but are outside the current software-development cohort.
- JobSearch retained only for exploratory use.
- Unit tests cover evidence rules, JobSearch helper, JobStream contract, raw landing, field profiling and experience-signal semantics; 23 tests passed at the latest validation gate.

No societal conclusion has been produced yet. That is intentional.

## 14. Change history

### 2026-10-18 — SQL Server persistence foundation validated

- Created the empty local development database `EventsToEvidence_Dev` and applied `sql/001_initial_schema.sql` with fail-fast execution.
- Verified 12 core user tables, 12 foreign keys, 7 check constraints and the two intended explicit indexes.
- Added and applied `sql/002_jobstream_source_persistence.sql`.
- Verified the extended model at 15 user tables, 17 foreign keys and 11 check constraints.
- Kept raw JobStream NDJSON/manifest files outside the normalized relational model and preserved batch lineage through `evidence_item -> ingestion_batch`.
- The source-specific extension stores provider occupation metadata, explicit analytical-cohort membership, preserved raw `experience_required`, validated experience-signal status and inspectable signal snippets. It does not create a junior-friendliness score.

### 2026-10-18 — Persistence technology correction

- Rechecked the original baseline before persistence implementation: the agreed direction was SQL-oriented storage while the database product and physical schema remained open.
- Withdrew the earlier provisional database-product choice before any project database or evidence rows were created.
- Selected Microsoft SQL Server for the first slice because it satisfies the current relational integrity, provenance, JSON-metadata, temporal and local-development requirements without requiring a second database platform.
- Retargeted `sql/001_initial_schema.sql` to SQL Server T-SQL using `NVARCHAR`, `DATETIMEOFFSET`, `BIT`, `ISJSON`, named constraints and transactional error handling.
- No current project requirement depends on a database-specific capability that would justify another relational engine.

### 2026-10-18 — First live-source validation and analytical cohort

- Ran the first real bounded Data/IT JobStream ingestion.
- Confirmed that the 93-event batch consists of 77 sparse removals and 16 full advertisements.
- Corrected a profiler denominator defect that had made full-ad fields appear only 17.2% complete.
- Verified corrected full-ad coverage and retained the raw batch unchanged.
- Rejected `experience_required` as a standalone accessibility signal because its documented no-experience semantics conflict with multiple ad texts in the real batch.
- Kept Data/IT as the acquisition boundary and set `Mjukvaru- och systemutvecklare m.fl.` (`DJh5_yyF_hEM`, 2512) as the current analytical cohort for the software-development question.
- Chose an explicit, auditable text-derived experience-signal route rather than manufacturing a junior/senior metric from sparse or contradictory structured fields.
- Implemented the first deterministic experience-signal audit with inspectable source snippets and cohort filtering.
- Manual validation of the first 9 cohort ads showed that all 9 contain some experience language, but only 7 contain an explicit quantified experience threshold and/or seniority signal; 2 contain qualitative experience language only. The audit therefore keeps these states separate rather than treating every experience mention as the same accessibility barrier.
- Manual review also exposed two context risks in generic experience wording: meritorious criteria and application instructions. The audit now keeps meritorious experience separate, carries a meritorious section across consecutive experience clauses until a clear mandatory-section reset, and excludes application prompts such as requests to describe the candidate's experience.
- Final validation against the same immutable 93-event batch passed with 23 automated tests and produced the expected 9-ad cohort split: 7 `explicit_threshold_or_seniority`, 2 `qualitative_experience_only`, 0 `meritorious_experience_only`, and 0 `unknown`. Application-instruction text was excluded, while consecutive experience clauses under `Meriterande` remained classified as meritorious.
- The source-defined 2512 cohort contains heterogeneous occupations, including IT project-management and application-consulting roles. Occupation concept remains an explicit analysis dimension so later aggregation does not silently treat the group as homogeneous.

### 2026-10-17 — Public identity and target description

- Adopted the display name **Events-to-Evidence Decision-Support Data Platform** and repository slug `events-to-evidence-decision-support-data-platform`.
- Froze the public target-system description recorded above after checking it against the baseline, Methodology Contract v2 and implementation-transition checkpoint.
- Clarified that the public description expresses intended whole-system value, while the current vertical slice remains the source of truth for what is implemented now.
- Clarified that AI is an orchestrator/support capability rather than an evidence authority, and that anticipation is conditional and not claimed for the current slice.
- Clarified that 'consistent evidence' means convergence after independence/ancestry and counter-evidence checks, not simple source count.
- Marked the former project title and old handover/checkpoint names as historical records rather than current identity.

### 2026-10-17 — Governance and implementation foundation

- Introduced this canonical living reference.
- Made documentation synchronization part of definition of done.
- Created minimum evidence/provenance domain model and initial relational schema.
- Created evidence-rule tests.

### 2026-10-17 — Technology correction

- Corrected an assistant-introduced drift: Power BI had never been an agreed technology for this project and is removed from the architecture assumptions.
- Clarified that the database product and `pytest` were new implementation choices, not earlier shared decisions.
- Recorded the governing rule that Data Engineering/system fit outranks showcasing .NET or any other framework.
- Left UI, API framework, .NET, cloud and containers open until requirements earn them.

### 2026-10-17 — Source-boundary correction

- Replaced JobSearch as the primary ingestion boundary with JobStream v2 after checking Arbetsförmedlingen's official API guidance.
- Added bounded NDJSON ingestion, immutable raw landing, manifest hashing and field-coverage profiling.
- Retained JobSearch only as an exploratory helper.

## 15. Exact next step

Implement the first **Python -> SQL Server persistence path** for the already-landed immutable JobStream batch `af-jobstream-20261018T092402Z-db19ff70`.

The loader must persist only what the validated source path has earned:

- register the observed-job-ads evidence family and Arbetsförmedlingen JobStream source;
- persist the existing raw batch manifest into `ingestion_batch`, including request parameters, retrieval time, raw path, SHA-256 and the 93-record count;
- persist the 16 full advertisements as `evidence_item` rows with source-record identity and raw-file lineage;
- preserve provider occupation field/group/occupation metadata for all 16 full ads;
- record explicit membership in the `DJh5_yyF_hEM` analytical cohort: 9 in-cohort and 7 out-of-cohort;
- preserve the raw provider `experience_required` value without translating it into accessibility truth;
- persist the validated deterministic experience-audit transformation and, for the 9 in-cohort ads, the derived status plus inspectable signal categories, source fields, matched text and snippets;
- keep the load idempotent so rerunning the same immutable batch does not duplicate evidence;
- perform post-load validation against the known batch totals and lineage before widening the source window.

Do not create an assessment, junior-friendliness score, wider historical window, UI, cloud deployment or second evidence family until this first persistence path is validated end to end.
