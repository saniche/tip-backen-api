# Implementation Plan: Application Journal

**Branch**: `005-application-journal` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-application-journal/spec.md`

## Summary

Add an authenticated journal for normalized jobs, backed by an owner/job-unique application
record and append-only status-history rows. The API projects job headers from the existing shared
catalog, supports editable application details and status progression, and performs database-side
listing with filtering and stable pagination. Creation uses the Interest Management
`release_interest()` helper in the same SQLAlchemy unit of work.

## Technical Context

**Language/Version**: Python 3.11+ (existing project runtime)

**Primary Dependencies**: FastAPI, Pydantic 2, SQLAlchemy 2, Alembic

**Storage**: Existing SQLite development/test and PostgreSQL production databases

**Testing**: pytest; contract, integration, unit, and migration tests

**Target Platform**: Existing Python API service

**Project Type**: REST API

**Performance Goals**: Owner-scoped listing performs database-side filter, count, stable sort, and
pagination; avoid N+1 job/history lookups for a page.

**Constraints**: Use existing bearer authentication, API error envelope, ORM conventions, UTC
timestamps, strict schemas, `page`/`limit` pagination, and migration chain. Do not add technology
dependencies or copy job header data.

**Scale/Scope**: One journal entry per authenticated user and normalized job; page size 20 by
default, maximum 100; no combined My Jobs endpoint.

## Constitution Check

- **Clear Service Contracts**: Pass. Request, response, error, filter, status, and pagination
  behavior are documented in [contracts/api-v1.md](./contracts/api-v1.md).
- **Test by Design**: Pass. Every user journey has acceptance scenarios, with focused automated
  tests planned in [tasks.md](./tasks.md).
- **Verify Integration Boundaries**: Pass. Router/auth, relational transaction, migration, and
  interest-release boundaries have contract/integration coverage.
- **Reuse Deliberately**: Pass. Reuse current `User`, `Job`, database session, auth dependency,
  error conventions, and `release_interest()` helper.
- **Keep Delivery Simple and Observable**: Pass. Add only two tables, one router/service/schema
  module set, and a reversible migration; use standard error translation and no new infrastructure.
- **Service constraints**: Pass. Keep FastAPI, Pydantic, SQLAlchemy, bearer authentication, and
  existing database engines.

No constitution violations or exceptions are required.

## Design Decisions

- `ApplicationJournal` stores ownership, job reference, recruiter JSON object, editable dates,
  work authorization flag, notes, status, and timestamps.
- `ApplicationStatusHistory` stores one initial event and each actual status change; the service
  exposes no history mutation.
- Only the authenticated owner can access or mutate an entry. The database unique constraint
  protects `(user_id, job_id)` even under concurrent creation.
- Create validates a completed job and inserts journal + initial history + scoped interest release
  before one commit.
- Status changes update current status and append a history row before one commit. Repeated status
  is a no-op for history.
- Journal list query joins `Job`, filters owner and optional escaped `ILIKE` terms, counts matching
  rows, sorts by `(created_at DESC, id DESC)`, and applies offset/limit before loading history for
  the returned page.
- History is returned ascending by `(date, id)`. Job header is projected from the current `Job`
  row.
- Add `009_application_journal` after `008_interest_listing_index`, with reversible schema,
  foreign keys, unique constraint, and list/history indexes.

## Project Structure

### Documentation (this feature)

```text
specs/005-application-journal/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api-v1.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
applications/
├── __init__.py
├── application_service.py
└── router.py

shared/
├── models.py
└── schemas.py

alembic/versions/
└── 009_application_journal.py

tests/
├── contract/test_application_contract.py
├── integration/test_application_workflow.py
└── unit/test_application_service.py
```

Modify `main.py` to mount the applications router. Extend migration coverage in
`tests/integration/test_migrations.py`.

**Structure Decision**: Add an `applications` domain module alongside existing `jobs`, `matching`,
and `profile` modules, with schemas/models in the established shared modules.

## Implementation Phases

1. Add status enum and application/history ORM models with uniqueness and supporting indexes.
2. Add reversible migration `009_application_journal`.
3. Add strict request/response schemas and service operations for create, list, retrieve, update,
   status change, and delete.
4. Add owner-scoped routes and mount the router in `main.py`.
5. Add contract, service, workflow, and migration tests; update quickstart if implementation
   conventions require adjustment.

## Validation

- Run focused unit, contract, integration, and migration tests for the application journal.
- Verify migration upgrade/downgrade on SQLite.
- Verify owner/job unique constraint and list/history indexes in migrated schema.
- Run Ruff on changed Python files and the full pytest suite if focused tests pass.

## Complexity Tracking

No constitution violations or unnecessary architectural complexity.
