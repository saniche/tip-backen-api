---

description: "Implementation tasks for the Application Journal feature"
---

# Tasks: Application Journal

**Input**: Design documents from `/specs/005-application-journal/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, and
`contracts/api-v1.md`

**Tests**: Included because the feature specification requires automated contract, integration,
unit, and migration scenarios.

**Organization**: Tasks are grouped by user story to support incremental implementation and
independent verification.

## Phase 1: Setup

**Purpose**: Create the domain module locations without introducing dependencies.

- [X] T001 Create `applications/__init__.py` as the application-journal domain package.
- [X] T002 [P] Add the application journal API tag and route paths to
  `specs/005-application-journal/contracts/api-v1.md`.

## Phase 2: Foundational

**Purpose**: Add the persistence foundation shared by all user stories.

- [X] T003 Add `ApplicationStatus`, `ApplicationJournal`, and `ApplicationStatusHistory` models,
  owner/job uniqueness, foreign keys, and list/history indexes in `shared/models.py`.
- [X] T004 Add reversible Alembic migration `alembic/versions/009_application_journal.py` after
  `008_interest_listing_index`, matching the models and data model.
- [X] T005 Extend `tests/integration/test_migrations.py` to assert the journal schema, unique
  constraint, indexes, and clean upgrade/downgrade while preserving existing data.
- [X] T006 Add strict recruiter, create, field-update, status-update, history, job-header, item, and
  paginated response schemas with camelCase aliases in `shared/schemas.py`.

**Checkpoint**: Base schema and request/response types are ready for independently testable API
stories.

## Phase 3: User Story 1 - Start Tracking an Application (Priority: P1) 🎯 MVP

**Goal**: Create a journal entry for a completed shared job; ensure initial history and optional
interest removal are atomic.

**Independent Test**: Create with and without an interest, trigger duplicate and invalid-job
failures, and verify stored journal/history/interest state.

### Tests for User Story 1

- [X] T007 [P] [US1] Add create contract tests for valid create, default status/history, missing
  job, unnormalized job, duplicate conflict, authentication, and owner/job uniqueness in
  `tests/contract/test_application_contract.py`.
- [X] T008 [P] [US1] Add service tests for insert defaults, `release_interest()` integration,
  absent-interest no-op, and transaction rollback when create or release fails in
  `tests/unit/test_application_service.py`.
- [X] T009 [P] [US1] Add workflow tests proving journal creation and interest removal commit or
  roll back together in `tests/integration/test_application_workflow.py`.

### Implementation for User Story 1

- [X] T010 Implement create service validation, owner association, initial history insert, scoped
  `release_interest()` call, uniqueness conflict translation, and single-commit behavior in
  `applications/application_service.py`.
- [X] T011 Implement authenticated `POST /api/v1/applications` with strict request/response
  handling in `applications/router.py`.
- [X] T012 Mount the applications router under `/api/v1` in `main.py`.

**Checkpoint**: Create succeeds without an interest, atomically releases an optional interest, and
rejects duplicates/invalid jobs.

## Phase 4: User Story 2 - Review My Application Journal (Priority: P1)

**Goal**: List and retrieve only the caller's entries with current job headers and chronological
history.

**Independent Test**: Seed two users and multiple jobs, exercise filters and pages, then verify
headers, history order, totals, and cross-user not-found behavior.

### Tests for User Story 2

- [X] T013 [P] [US2] Add list/retrieve contract tests for owner isolation, current job projection,
  chronological history, default ordering/page size, all filters and AND semantics, wildcard
  escaping, maximum limit, empty pages, and pagination metadata in
  `tests/contract/test_application_contract.py`.
- [X] T014 [P] [US2] Add service tests proving filters, count, stable sort, and pagination are
  executed by the database in `tests/unit/test_application_service.py`.
- [X] T015 [P] [US2] Add workflow tests for equal creation/history timestamps and job header changes
  reflected in journal responses in `tests/integration/test_application_workflow.py`.

### Implementation for User Story 2

- [X] T016 Implement owner-scoped detail retrieval and database-side filtered/count/page list
  queries with current job headers and eager/batched history retrieval in
  `applications/application_service.py`.
- [X] T017 Implement authenticated `GET /api/v1/applications` and
  `GET /api/v1/applications/{application_id}` in `applications/router.py`.

**Checkpoint**: List and detail expose only owner records, with current headers and stable,
filtered, database-paginated results.

## Phase 5: User Story 4 - Record Status Progress (Priority: P1)

**Goal**: Append an immutable history event only when the current status changes.

**Independent Test**: Change status, query the entry and history, repeat the status, and simulate
a failed history write to validate the transaction invariant.

### Tests for User Story 4

- [X] T018 [P] [US4] Add status contract tests for every accepted value, invalid values, optional
  note, unchanged-status no-op, foreign-owner not-found, and response history ordering in
  `tests/contract/test_application_contract.py`.
- [X] T019 [P] [US4] Add service/integration tests for atomic current-status update and history
  append, status/history consistency, retained events, and rollback in
  `tests/unit/test_application_service.py` and `tests/integration/test_application_workflow.py`.

### Implementation for User Story 4

- [X] T020 Implement owner-scoped status update and append-only history insertion in one
  transaction; skip history when status is unchanged in `applications/application_service.py`.
- [X] T021 Implement authenticated `PATCH /api/v1/applications/{application_id}/status` in
  `applications/router.py`.

**Checkpoint**: Every actual status change is atomic with its history entry; no redundant events
are created and existing history is retained.

## Phase 6: User Story 3 - Maintain Application Details (Priority: P2)

**Goal**: Partially update recruiter information, dates, work authorization discussion, and notes
without changing status history.

**Independent Test**: Update each editable field, including clearing nullable values, then verify
omitted fields and all history entries remain unchanged.

### Tests for User Story 3

- [X] T022 [P] [US3] Add field-update contract tests for partial updates, nullable clears,
  recruiter validation, forbidden `status`/`history`/`jobId`/`userId` input, invalid dates, and
  owner isolation in `tests/contract/test_application_contract.py`.
- [X] T023 [P] [US3] Add service tests proving non-status updates preserve current status and
  history in `tests/unit/test_application_service.py`.

### Implementation for User Story 3

- [X] T024 Implement allow-listed partial update semantics using `exclude_unset`, validate
  recruiter object fields, and avoid status/history mutation in
  `applications/application_service.py`.
- [X] T025 Implement authenticated `PATCH /api/v1/applications/{application_id}` in
  `applications/router.py`.

**Checkpoint**: Editable fields can be changed or cleared without altering any status history.

## Phase 7: User Story 5 - Remove an Application Entry (Priority: P3)

**Goal**: Delete a journal record and its history without affecting the shared job or recreating an
interest.

**Independent Test**: Delete one owned entry and verify the job remains, history is removed, and
the interest remains absent.

### Tests for User Story 5

- [X] T026 [P] [US5] Add delete contract/workflow tests for success, foreign-owner and missing IDs,
  preserved normalized job, deleted journal history, and no interest recreation in
  `tests/contract/test_application_contract.py` and
  `tests/integration/test_application_workflow.py`.

### Implementation for User Story 5

- [X] T027 Implement owner-scoped journal deletion with history cleanup and no job/interest changes
  in `applications/application_service.py`.
- [X] T028 Implement authenticated `DELETE /api/v1/applications/{application_id}` with `204`
  response in `applications/router.py`.

**Checkpoint**: Journal deletion is private and does not modify the normalized job or interests.

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validate the full feature and align documentation with delivered behavior.

- [X] T029 [P] Update `specs/005-application-journal/quickstart.md` if focused test commands or
  response behavior changed during implementation.
- [X] T030 Run focused application contract, service, workflow, and migration tests; fix failures
  in the corresponding implementation/test files.
- [X] T031 Run Ruff on changed Python files and the full pytest suite; resolve regressions in
  changed files.
- [X] T032 Verify migration downgrade/upgrade, schema uniqueness/indexes, and original
  `jobs/job_normalizer.py` working-tree edits remain untouched.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No implementation dependencies; repository already has required framework
  and test conventions.
- **Foundational (Phase 2)**: Blocks all API user stories.
- **User Stories (Phases 3-7)**: Depend on the schema, migration, and shared request/response models.
  Stories can follow the listed P1-to-P3 order.
- **Polish (Phase 8)**: Depends on all selected user stories.

### User Story Dependencies

- **US1 (P1)**: Depends on foundational models/schemas; delivers entry creation and transactional
  interest release.
- **US2 (P1)**: Depends on US1 persistence and response models; retrieves existing journal records.
- **US4 (P1)**: Depends on US1 history persistence; adds status-change events.
- **US3 (P2)**: Depends on US1 entry retrieval/update schema; does not depend on status updates.
- **US5 (P3)**: Depends on parent/history relationship and owner-scoped retrieval.

### Parallel Opportunities

- T007-T009 can be authored in parallel after the model/schema contracts are established.
- T013-T015 are separate test files or concerns and can be prepared in parallel.
- T018-T019 and T022-T023 can be prepared in parallel within their story phases.
- Stories US3 and US4 are separable after foundational setup; US2 and US5 depend on persisted
  entry/history structure.

## Parallel Example: User Story 1

```text
Task: Add create contract tests in tests/contract/test_application_contract.py
Task: Add service transaction tests in tests/unit/test_application_service.py
Task: Add atomic workflow tests in tests/integration/test_application_workflow.py
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete shared model, migration, and schema foundation.
2. Add create contract, unit, and integration tests.
3. Implement journal creation plus initial status history and atomic interest release.
4. Validate missing interest, duplicate, invalid job, and rollback cases.

### Incremental Delivery

1. Add listing/detail and verify owner scoping, job header projection, filters, and pagination.
2. Add status updates and validate current/history transaction invariants.
3. Add editable field updates without status history changes.
4. Add deletion, then run full validation and migration round trips.
