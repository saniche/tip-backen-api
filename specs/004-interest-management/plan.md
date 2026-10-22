# Implementation Plan: Interest Management

**Branch**: `004-interest-management` | **Date**: 2026-10-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-interest-management/spec.md`

## Summary

Complete the existing, create-only interest capability: add an owner-scoped, filterable, paginated listing (`GET /api/v1/jobs/interests`), a removal operation (`DELETE /api/v1/jobs/{job_id}/interest`), automatic interest creation committed atomically with successful job normalization, and a non-committing `release_interest` operation the future Application Journal will call inside its own transaction. Business rules move into a new `jobs/interest_service.py`; routes stay in the existing jobs router. The existing `JobInterest` model and uniqueness constraints are reused; one new index migration is added. No new technology or component is introduced.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, Pydantic 2, SQLAlchemy 2, Alembic (all existing)

**Storage**: Existing `job_interests` and `jobs` tables; SQLite for tests/local, PostgreSQL deployed

**Testing**: pytest with FastAPI `TestClient`, in-memory SQLite, fake structured-AI provider; Ruff (line length 120)

**Target Platform**: Linux container (`python:3.11-slim`)

**Project Type**: Python web service

**Performance Goals**: 95% of listing requests return within 2 seconds for users with up to 10,000 interests (spec SC-008)

**Constraints**: Default page 1, default limit 20, maximum 100; filtering, counting, sorting, and paging in the database; standard error envelope; existing bearer authentication; existing `POST /jobs/{id}/interest` route and response shape preserved; interest creation committed with normalization completion

**Scale/Scope**: One index migration, three routes (one new list, one new delete, one hardened add), one service module, one schema group, one change to the normalization workflow, one change to job deletion

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / constraint | Gate result | Plan evidence |
|---|---|---|
| I. Clear Service Contracts | PASS | New routes, parameters, response envelope, and errors are documented in [contracts/api-v1.md](./contracts/api-v1.md); the existing add route is backward compatible and the only behavior change (409 for non-completed jobs) is documented. |
| II. Test by Design | PASS | Contract, integration, and unit test files are planned with the behavior (see Structure and the spec's Automated Test Scenarios), covering results, validation failures, and edge cases. |
| III. Verify Integration Boundaries | PASS | Router + persistence + authentication are tested through the HTTP boundary; the normalization workflow, migration, and journal-atomicity boundaries have integration tests. |
| IV. Reuse Deliberately | PASS | Reuses `JobInterest`, `Job`, `get_current_user`, `get_db`, 003's pagination vocabulary and escaped-pattern filter helper, and the existing failure path. Shared rules live in one service module. |
| V. Keep Delivery Simple and Observable | PASS | One commit gives atomicity; no events, queues, savepoints, or new dependencies. Failures reuse existing logging and user-safe messages without exposing user data. |
| Service constraints | PASS | FastAPI/Pydantic/SQLAlchemy retained; authentication required on every operation; ownership derived only from the authenticated user; no secrets logged. |

No violations; Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/004-interest-management/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api-v1.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
jobs/
├── interest_service.py              # NEW: ensure, remove, release, list query (release never commits)
└── job_normalizer.py                # Add list + delete routes; harden add; auto-interest on completion and existing-job path; delete interests on job delete
shared/
├── models.py                        # Add composite index to JobInterest __table_args__
└── schemas.py                       # Add InterestJobHeader, InterestItem, InterestsPage (camelCase aliases)
alembic/versions/
└── 008_interest_listing_index.py    # NEW: ix_job_interests_user_created
tests/
├── contract/
│   ├── test_interest_contract.py    # NEW: list/add/remove, filters, pagination, isolation, auth, validation
│   └── test_job_contract.py         # Extend: first add now reports "existing"; job delete removes interests
├── integration/
│   ├── test_interest_workflow.py    # NEW: auto-interest, resubmission, two users, forced failure, release atomicity, DB-side paging
│   └── test_migrations.py           # Extend: new index present, revision id length, downgrade
└── unit/
    └── test_interest_service.py     # NEW: ensure/release semantics, pagination math, filter escaping
```

**Structure Decision**: Extend the existing jobs router and shared schemas, adding one small service module for reusable business rules. `GET /jobs/interests` is declared before `GET /jobs/{job_id}` (next to `/normalized`). The escaped contains-pattern helper currently in `job_normalizer.py` is shared with the service so 003 and this feature use one implementation.

## Design Decisions

Full rationale and alternatives are in [research.md](./research.md).

- **Service API** (`jobs/interest_service.py`): `ensure_interest(db, user_id, job_id)` returns the interest and whether it was created (select, then insert + flush, no commit); `remove_interest(db, user_id, job_id) -> bool` (scoped delete); `release_interest(db, user_id, job_id) -> bool` (same scoped delete, documented as the journal hook, never commits); `list_interests(db, user_id, *, title, company, location, page, limit)` returns rows and total using one join and a matching count.
- **Add route**: 404 missing job, 409 non-completed job, commit; on `IntegrityError` roll back and return the existing interest; response shape unchanged.
- **Remove route**: scoped delete; 404 if no row; 204 otherwise; never touches the job.
- **List route**: `page >= 1`, `1 <= limit <= 100`, default 20; filters trimmed and escaped; envelope `items`, `total`, `page`, `limit`, `totalPages`; `job` projection includes `id, title, company, location, url, source, postingDate`.
- **Normalization success**: `ensure_interest` for `processing_job.user_id` immediately before the final commit; failures use the existing rollback/failed handling.
- **Submission of an existing job**: if `status == "completed"`, ensure the interest and commit before responding `existing`; otherwise unchanged.
- **Job deletion**: delete the job's interests, then the job, in one transaction.
- **Migration**: `008_interest_listing_index` after `007_job_additionals`, reversible, SQLite and PostgreSQL compatible.
- **Observability**: interest-creation failures during normalization go through the existing normalization error log (job and processing-job identifiers only, no user data).

## Constitution Check (Post-Design)

| Principle / constraint | Gate result | Design evidence |
|---|---|---|
| I. Clear Service Contracts | PASS | Contract file defines list, add, remove, normalization side effects, and the internal release capability. |
| II. Test by Design | PASS | Each user story and edge case in the spec maps to a planned contract, integration, or unit test. |
| III. Verify Integration Boundaries | PASS | Failure injection at the persistence boundary during normalization and a simulated journal transaction are included. |
| IV. Reuse Deliberately | PASS | One service module serves routes, the background workflow, and the journal; the filter helper is shared with 003. |
| V. Keep Delivery Simple and Observable | PASS | Single-commit atomicity, no new infrastructure, reuse of existing failure handling. |
| Service constraints | PASS | Authentication on all routes, ownership enforced in every query, standard validation and error envelope. |

No gates failed; ready for `/speckit-tasks`.
