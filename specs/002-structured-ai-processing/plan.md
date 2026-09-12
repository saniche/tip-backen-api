# Implementation Plan: Structured AI Processing

**Branch**: `002-structured-ai-processing` | **Date**: 2026-09-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification for validated OpenAI-backed profile, job, matching, and CV processing.

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Replace local heuristics in profile building, job normalization, job matching, and CV tailoring
with OpenAI strict structured-output calls. Each operation owns a Pydantic output model and
prompt, validates before adapting into existing domain data, and retains current HTTP routes.
Profile, job, and CV remain background jobs; matching becomes asynchronous internally and commits
only after all selected assessments validate.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+ (interpreter version to confirm during implementation)

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2, httpx, python-dotenv

**Storage**: PostgreSQL or SQLite via SQLAlchemy; Azure Blob Storage or development fallback for CVs

**Testing**: pytest and FastAPI TestClient; mock async provider calls

**Target Platform**: Local or containerized HTTP web service

**Project Type**: Web service

**Performance Goals**: 95% of completed processing reaches a final state within 60 seconds under normal provider conditions

**Constraints**: Use OpenAI Chat Completions strict `json_schema` through existing `httpx` helper; schema objects forbid extras and require all fields; no secrets, raw provider output, or unredacted candidate text in logs/errors

**Scale/Scope**: Four operations, four output schemas, and four configured model identifiers; no public-route or database migration change

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Plan response | Status |
|-----------|---------------|--------|
| Clear Service Contracts | Preserve routes and response models; translate provider failures to the existing safe error shape. | Pass |
| Test by Design | Test valid responses, invalid structured output, unavailable provider, and unsupported facts for every operation. | Pass |
| Verify Integration Boundaries | Keep OpenAI calls in `llm_structured.py`, mock them in normal tests, and add focused boundary coverage. | Pass |
| Reuse Deliberately | Reuse helper, domain dataclasses, persistence models, error translator, and job flow. | Pass |
| Keep Delivery Simple and Observable | One provider boundary, per-operation configuration, bounded timeout, and metadata-only diagnostics. | Pass |

**Post-design check**: Pass. No route or persistence migration is introduced.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
job-process-api/
├── llm_structured.py                  # shared OpenAI structured-output boundary
├── job_service.py                     # job schema and adapter
├── matching_service.py                # asynchronous match persistence
├── profile_builder_router.py          # profile background worker
├── job_normalizer.py                  # job background worker
├── job_matching_router.py             # matching routes
├── cv_tailoring_router.py             # CV background worker
├── pipeline/
│   ├── profile_builder.py             # profile schema and adapter
│   ├── llm_matching.py                # matching schema and adapter
│   └── cv_tailoring.py                # CV schema and adapter
├── tests/
│   ├── unit/
│   └── integration/
└── specs/002-structured-ai-processing/
  ├── plan.md
  ├── research.md
  ├── data-model.md
  ├── quickstart.md
  └── contracts/api-v1.md
```

**Structure Decision**: Keep the existing single-module FastAPI layout. Each operation's strict
output model stays beside its domain adapter; `llm_structured.py` remains the only provider boundary.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations require justification.
