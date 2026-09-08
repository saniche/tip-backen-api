# Implementation Plan: Talent Intelligence Platform

**Branch**: `001-talent-intelligence-platform` | **Date**: 2026-09-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification and `Docs/T_I_Platform_Technical_Architecture_V1.1.md`

## Summary

Deliver the V1 Talent Intelligence Platform as a versioned REST service that securely owns user
career data, processes profiles and jobs asynchronously, calculates matching deterministically,
and produces grounded tailored CVs. The existing FastAPI service retains its routers while placing
orchestration, AI adapters, scoring, storage, and persistence behind clear boundaries.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: FastAPI, Pydantic 2.x, SQLAlchemy 2.x, python-jose, passlib,
azure-storage-blob, httpx, and a provider-isolated OpenAI adapter

**Storage**: PostgreSQL 15+ for structured data and Azure Blob Storage for source documents and
generated CVs

**Testing**: pytest; unit tests for rules and state transitions, API tests for contracts and
authorization, and integration tests for persistence, storage, AI adapters, and background tasks

**Target Platform**: Containerized Linux web service, deployed to Azure with HTTPS

**Project Type**: Versioned REST web service

**Performance Goals**: Profile sessions of up to five typical documents report completion or
failure within 10 minutes for at least 95% of successful sessions.

**Constraints**: `/api/v1` contract; stateless requests; FastAPI BackgroundTasks in V1; PDF,
DOCX, and TXT uploads up to configurable 10 MB; no distributed broker or worker is required.

**Scale/Scope**: One API instance for V1; four capability areas (profile processing, job
normalization, matching, and CV tailoring); shared jobs and user-owned personal records.

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

**Pre-design gate: PASS**

- Clear service contracts: the versioned REST surface and common error format are in
  [contracts/api-v1.md](contracts/api-v1.md).
- Test by design: [quickstart.md](quickstart.md) defines acceptance, authorization, duplicate,
  and full-flow validation; implementation must add focused automated tests.
- Integration boundaries: PostgreSQL, blob storage, authentication, and AI provider calls remain
  behind testable modules and require boundary tests.
- Reuse: routers use shared schemas, serialization, scoring, authentication, storage, and AI
  abstractions; route handlers do not duplicate business rules.
- Simplicity and observability: V1 uses BackgroundTasks, persisted processing states, safe errors,
  request correlation, and structured logging.

**Post-design gate: PASS**

The data model preserves ownership and historical matching context; the REST contract has explicit
authentication, authorization, status, and safe-error behavior; and the quickstart requires unit,
contract, integration, authorization, and end-to-end coverage. All external boundaries are named
for isolation behind reusable modules, with no constitution exception required.

## Project Structure

### Documentation (this feature)

```text
specs/001-talent-intelligence-platform/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
auth.py                         # tokens, passwords, identity dependency
auth_router.py                  # registration and login routes
profile_builder_router.py       # profile-session API and background orchestration
job_normalizer.py               # normalized-job API
job_matching_router.py          # matching API
cv_tailoring_router.py          # CV tailoring API
download_router.py              # authorized CV downloads
processing_jobs_router.py       # processing-status API
models.py                       # SQLAlchemy persistence models
schemas.py                      # shared request and response schemas
serialization.py                # profile persistence mapping
database.py                     # database session and declarative base
storage.py                      # application-owned blob storage abstraction
llm_structured.py               # provider-isolated structured AI operations
tests/
├── unit/
├── contract/
└── integration/
```

**Structure Decision**: Keep the existing single-project, flat Python service for V1. Add focused
reusable modules beneath the repository root as needed for profile, job, matching, and CV business
rules; routers remain thin HTTP adapters. Do not introduce a frontend, distributed worker, or
second project in this feature.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --------- | ---------- | ------------------------------------ |
| None      | N/A        | N/A                                  |
