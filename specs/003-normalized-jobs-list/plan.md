# Implementation Plan: Normalized Jobs Listing

**Branch**: `003-normalized-jobs-list` | **Date**: 2026-10-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-normalized-jobs-list/spec.md`

## Summary

Add an authenticated `GET /api/v1/jobs/normalized` listing alongside the existing jobs list. It returns only the six requested header fields for successfully normalized global jobs, supports title/company/location substring filters, returns pagination metadata with a default page size of 20, and sorts by posting date descending. The implementation reuses the existing SQLAlchemy `Job` records and FastAPI authentication; it requires no new storage or migration.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI, Pydantic 2, SQLAlchemy 2

**Storage**: Existing `jobs` table in SQLite for tests/local use and PostgreSQL in deployed environments

**Testing**: pytest with FastAPI `TestClient`; focused contract tests and Ruff

**Target Platform**: Linux container, Python 3.11 slim image

**Project Type**: Python web service

**Performance Goals**: Meet the specification target: at least 95% of listing requests return a page or empty result within 2 seconds under normal service load.

**Constraints**: Keep the existing `/api/v1/jobs` behavior unchanged; require existing bearer authentication; page defaults to 1, limit defaults to 20 and is bounded from 1 to 100; job items contain exactly six fields.

**Scale/Scope**: Read from the existing shared, URL-deduplicated job catalog; no new persisted entities or schema migration.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / constraint | Gate result | Plan evidence |
|---|---|---|
| Clear Service Contracts | PASS | The new route, request parameters, response envelope, item fields, filtering, ordering, and error behavior are specified in [contracts/api-v1.md](./contracts/api-v1.md). |
| Test by Design | PASS | Contract tests cover filtering, pagination, ordering, exact item shape, and validation. |
| Verify Integration Boundaries | PASS | Authenticated route behavior and database-backed results are tested through the API boundary. |
| Reuse Deliberately | PASS | Reuse the existing `Job` model, SQLAlchemy session dependency, and authentication dependency; add narrowly typed response schemas. |
| Keep Delivery Simple and Observable | PASS | The feature is read-only, uses existing storage, introduces no external dependencies, and relies on standard request validation and service error behavior. |
| Service constraints | PASS | Retains FastAPI, Pydantic, SQLAlchemy, and the existing authentication requirement; no secrets or sensitive data are logged. |

No constitution violations or exceptions are required.

## Project Structure

### Documentation (this feature)

```text
specs/003-normalized-jobs-list/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── api-v1.md
```

### Source Code (repository root)

```text
jobs/
└── job_normalizer.py                 # Add the normalized listing route
shared/
└── schemas.py                        # Add typed header item and paginated response schemas
tests/
└── contract/
    ├── test_normalized_jobs_contract.py  # New listing contract coverage
    └── test_job_contract.py              # Existing listing regression coverage
```

**Structure Decision**: Extend the existing jobs router and shared Pydantic schemas. The router is already included under `/api/v1` in `main.py`; no router registration or database model changes are needed. Register the static `/normalized` route before the existing `/{job_id}` route so it is matched as a listing route rather than a job identifier.

## Design Decisions

- Filter and count successful (`completed`) jobs from the global catalog, applying all supplied filters together.
- Return a typed pagination envelope with the existing `items`, `total`, `page`, and `limit` vocabulary. Each item serializes only `id`, `title`, `company`, `location`, `postingDate`, and `source`.
- Keep pagination bounds aligned with the existing jobs listing, while setting this listing's default limit to 20.
- Preserve the existing jobs listing contract and behavior.
- Order valid posting dates newest-first, put missing or unparseable values last, and use `id` ascending as a deterministic tie-breaker. Since the stored posting date is text and the catalog may include invalid values, use date-aware ordering rather than relying on database-specific text casts; keep selection to the small header projection and apply database filters before ordering.

## Constitution Check (Post-Design)

| Principle / constraint | Gate result | Design evidence |
|---|---|---|
| Clear Service Contracts | PASS | The contract documents exact request, response, and error behavior. |
| Test by Design | PASS | Test scenarios map to each externally observable behavior and preserve a regression test for the existing route. |
| Verify Integration Boundaries | PASS | Contract tests exercise authentication, query validation, and persisted job data through the HTTP boundary. |
| Reuse Deliberately | PASS | The design reuses existing models and dependencies and adds only endpoint-specific typed schemas. |
| Keep Delivery Simple and Observable | PASS | No migration, new infrastructure, or external service is introduced. |
| Service constraints | PASS | Existing framework and authentication conventions are retained. |

No gates failed; implementation may proceed to task generation.
