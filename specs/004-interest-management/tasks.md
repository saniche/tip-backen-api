---

description: "Implementation tasks for Interest Management"
---

# Tasks: Interest Management

**Input**: Design documents from `specs/004-interest-management/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api-v1.md`, `quickstart.md`

**Tests**: Required by the project constitution (Test by Design, Verify Integration Boundaries). Tests are written before the implementation they cover in each story phase.

**Organization**: Tasks are grouped by the four user stories in `spec.md`. US1–US3 are P1 and independent of each other once Phase 2 is complete; US4 is P2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks in the same phase (different files, no incomplete prerequisites).
- **[Story]**: Maps a task to its user story (US1–US4).
- Every task names its target file. Use the project virtual environment: `.\.venv\Scripts\python.exe -m pytest ...`.

## Path Conventions

Single Python web service: application code in `jobs/`, `shared/`, `alembic/versions/`; tests in `tests/contract/`, `tests/integration/`, `tests/unit/`.

---

## Phase 1: Setup

**Purpose**: Establish a green baseline before changes.

- [X] T001 Run the existing suite (`.\.venv\Scripts\python.exe -m pytest -q`) and `.\.venv\Scripts\python.exe -m ruff check .` from the repository root and record any pre-existing failures so they are not attributed to this feature

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema, response types, and the shared service module that every story depends on.

- [X] T002 Add `Index("ix_job_interests_user_created", "user_id", "created_at", "id")` to `JobInterest.__table_args__` (keeping `uq_job_interest_user_job`) and import `Index` in `shared/models.py`
- [X] T003 [P] Create migration `alembic/versions/008_interest_listing_index.py` (`revision = "008_interest_listing_index"`, `down_revision = "007_job_additionals"`) with `upgrade` creating `ix_job_interests_user_created` on `job_interests(user_id, created_at, id)` and `downgrade` dropping it
- [X] T004 [P] Add `InterestJobHeader` (`id`, `title`, `company`, `location`, `url`, `source`, `postingDate` via serialization alias), `InterestItem` (`id`, `jobId`, `createdAt`, `job`), and `InterestsPage` (`items`, `total`, `page`, `limit`, `totalPages`) Pydantic models, following `NormalizedJobHeader` conventions (`extra="forbid"`, `populate_by_name=True`), in `shared/schemas.py`
- [X] T005 Create `jobs/interest_service.py` containing `contains_pattern(value)` (the escaped `%value%` helper moved from `_contains_pattern` in `jobs/job_normalizer.py`) and `ensure_interest(db, user_id, job_id) -> tuple[JobInterest, bool]` (select the caller's row first; otherwise add and `flush`; never commit); update `jobs/job_normalizer.py` to import `contains_pattern` from the service and remove its private copy so `GET /jobs/normalized` behavior is unchanged
- [X] T006 [P] Add migration tests in `tests/integration/test_migrations.py`: `008_interest_listing_index.py` exists, its revision id is ≤ 32 characters, `ix_job_interests_user_created` is in `PRAGMA index_list('job_interests')` after `alembic upgrade head`, and is absent after `alembic downgrade -1`
- [X] T007 [P] Add unit tests in `tests/unit/test_interest_service.py` for `contains_pattern` (strips whitespace, escapes `%`, `_`, `\`) and `ensure_interest` (creates once, returns `(existing, False)` on repeat, separate rows for different users, does not commit — verified by rolling back and finding no row)

**Checkpoint**: Schema, index, response types, and `ensure_interest` are available; `.\.venv\Scripts\python.exe -m pytest tests\unit\test_interest_service.py tests\integration\test_migrations.py tests\contract\test_normalized_jobs_contract.py -q` passes.

---

## Phase 3: User Story 1 - Review My Interests (Priority: P1) 🎯 MVP

**Goal**: An authenticated user lists only their own interests, newest first, with job header information, filters, and pagination metadata, all computed in the database.

**Independent Test**: Seed interests for two users (using shared jobs), list as one user, and verify isolation, ordering, header fields, filters, pagination metadata, empty and out-of-range pages, and validation errors.

### Tests for User Story 1

- [X] T008 [P] [US1] Add list contract tests in `tests/contract/test_interest_contract.py`: `401` without token; only the caller's interests and `total`; item shape (`id`, `jobId`, `createdAt`, `job` with `id`, `title`, `company`, `location`, `url`, `source`, `postingDate`) with `null` optional fields; default `page=1`, `limit=20`, newest-first order; equal `created_at` ordered by `id` descending; `company`/`title`/`location` filters individually and combined (AND), case-insensitive partial match, blank filter ignored, `%`/`_` matched literally; `limit` and `page` paging with correct `totalPages`; page beyond last returns empty `items` with unchanged `total`; no matches returns `total=0`, `totalPages=0`; `page=0`, `limit=0`, `limit=101` return `422`; a job title edit is reflected in the listing
- [X] T009 [P] [US1] Add unit tests in `tests/unit/test_interest_service.py` for `list_interests`: total-pages arithmetic (including zero), owner scoping, filters combined, and stable ordering with identical timestamps
- [X] T010 [P] [US1] Add a DB-side paging test in `tests/integration/test_interest_workflow.py` that seeds more than one page of interests, records executed statements with a SQLAlchemy `before_cursor_execute` listener, and asserts the listing issues exactly one count statement and one page statement whose SQL contains `LIMIT`/`OFFSET`, `ORDER BY`, and the owner/filter predicates (no per-row job lookups)

### Implementation for User Story 1

- [X] T011 [US1] Add `list_interests(db, user_id, *, title, company, location, page, limit)` to `jobs/interest_service.py`: one `select(JobInterest, Job)` joined on `Job.id == JobInterest.job_id`, `JobInterest.user_id == user_id`, `ilike(contains_pattern(...), escape="\\")` filters for non-blank values, `order_by(JobInterest.created_at.desc(), JobInterest.id.desc())`, `offset((page - 1) * limit).limit(limit)`, plus a matching `count` statement; return the rows and total
- [X] T012 [US1] Add `GET /interests` to `jobs/job_normalizer.py` (`response_model=InterestsPage`, `page: int = Query(1, ge=1)`, `limit: int = Query(20, ge=1, le=100)`, optional `title`, `company`, `location`, `Depends(get_current_user)`), declared next to `/normalized` and before `/{job_id}`, mapping rows to `InterestItem` and computing `totalPages = ceil(total / limit)` (`0` when `total` is `0`)

**Checkpoint**: `GET /api/v1/jobs/interests` is independently usable; T008–T010 pass and `tests/contract/test_normalized_jobs_contract.py` still passes.

---

## Phase 4: User Story 2 - Add and Remove an Interest (Priority: P1)

**Goal**: A user adds a normalized job to their interests (idempotently) and removes their own interest without touching the job; other users' interests are untouched.

**Independent Test**: Add a normalized job twice (one interest), reject unknown and non-normalized jobs, remove it (job still retrievable), and verify another user's removal attempt returns `404` and leaves the interest.

### Tests for User Story 2

- [X] T013 [P] [US2] Add add/remove contract tests in `tests/contract/test_interest_contract.py`: add returns `201` `created` then `201` `existing` with one listed interest; unknown job `404`; `pending`/`processing`/`failed` job `409` and no interest created; unauthenticated add/remove `401`; remove returns `204` and the job is still returned by `GET /api/v1/jobs/{id}`; remove with no interest `404`; remove of another user's interest `404` while that interest remains in their list; removed interest no longer listed; a second user's interest in the same job is unaffected
- [X] T014 [P] [US2] Add unit tests in `tests/unit/test_interest_service.py` for `remove_interest` (returns `True` once then `False`, only the caller's row is deleted, job row untouched)
- [X] T015 [P] [US2] Add integration tests in `tests/integration/test_interest_workflow.py` that a simultaneous-add `IntegrityError` (simulated by inserting the row between the existence check and the insert) resolves to `status: "existing"` rather than a server error, and that the database rejects a duplicate `(user_id, job_id)` row directly
- [X] T016 [P] [US2] Extend `tests/contract/test_job_contract.py` with a test that deleting a job (as submitter) also removes interests that users hold in it, and returns `204` (FR-024)

### Implementation for User Story 2

- [X] T017 [US2] Add `remove_interest(db, user_id, job_id) -> bool` to `jobs/interest_service.py` using a scoped `delete(JobInterest).where(user_id == ..., job_id == ...)` and returning whether a row was deleted (no commit)
- [X] T018 [US2] In `jobs/job_normalizer.py` harden `POST /{job_id}/interest`: `404` if the job is missing, `409` if `job.status != "completed"`, use `ensure_interest`, commit, and on `IntegrityError` roll back and return the existing interest as `status: "existing"`; keep the `201` status and the `{"id", "status"}` body unchanged
- [X] T019 [US2] In `jobs/job_normalizer.py` add `DELETE /{job_id}/interest` (`status_code=204`): call `remove_interest` with `current_user.id`, `404 "Interest not found"` when nothing was deleted, commit otherwise, and never touch the `Job` row
- [X] T020 [US2] In `delete_job` in `jobs/job_normalizer.py`, delete the job's `JobInterest` rows before deleting the job within the same transaction

**Checkpoint**: Add and remove behave per the contract; T013–T016 pass; existing `tests/contract/test_job_contract.py` still passes.

---

## Phase 5: User Story 3 - Interest Created Automatically After Normalization (Priority: P1)

**Goal**: A successful normalization adds the job to the submitter's interests in the same commit as completion; repeated submissions never duplicate; failures never report success.

**Independent Test**: Submit a new job, confirm exactly one interest after completion; resubmit; submit as a second user; force interest-creation and normalization failures and confirm failed status with no interest.

### Tests for User Story 3

- [X] T021 [P] [US3] Add normalization-workflow tests in `tests/integration/test_interest_workflow.py`: new job yields exactly one interest for the submitter after completion; same-user resubmission leaves one interest; a second user's submission of the same URL yields their own interest on the same single job; failed normalization (monkeypatch `jobs.job_normalizer.normalize_job_content` to raise `StructuredProviderError`) creates no interest; forced interest failure (monkeypatch `jobs.job_normalizer.ensure_interest` to raise) leaves the processing job `failed`, the job `failed` (not `completed`), and no interest; an existing job that is not `completed` creates no interest from a resubmission; an interest-write failure on the existing-completed path returns the standard error response, not a success
- [X] T022 [P] [US3] Update `test_job_deduplication_filters_and_interest` in `tests/contract/test_job_contract.py` so it asserts the first manual add now returns `status: "existing"` (interest was created by normalization) and that the interest appears in `GET /api/v1/jobs/interests`

### Implementation for User Story 3

- [X] T023 [US3] In `_run_job_normalization` in `jobs/job_normalizer.py`, after applying structured fields and before the final `db.commit()`, call `ensure_interest(db, processing_job.user_id, job.id)` so job completion, processing `DONE`, and the interest commit together; rely on the existing `except` path for rollback and `failed` statuses; import `ensure_interest` into the module namespace so tests can patch it
- [X] T024 [US3] In `normalize_job` in `jobs/job_normalizer.py`, when an existing job has `status == "completed"`, call `ensure_interest(db, current_user.id, existing.id)` and commit before returning `{"id": existing.id, "status": "existing"}`; leave the response unchanged for non-completed existing jobs and create no interest for them

**Checkpoint**: Normalization creates interests atomically; T021–T022 pass together with `tests/integration/test_job_normalization.py`.

---

## Phase 6: User Story 4 - Interest Released When an Application Is Created (Priority: P2)

**Goal**: Provide the non-committing interest-release capability the Application Journal will call inside its own transaction.

**Independent Test**: In one transaction, simulate a journal write plus `release_interest`; verify commit applies both, rollback restores both, a missing interest is a no-op, and the job survives.

### Tests for User Story 4

- [X] T025 [P] [US4] Add `test_release_interest_is_atomic_with_journal_write` and related cases in `tests/integration/test_interest_workflow.py` using a stand-in journal record (a test-only table or object created in the test) written in the same session: commit removes the interest and keeps the record; a failing record write rolls back so the interest remains; a failing release prevents the record; releasing when no interest exists is a no-op and the record is still created; the job and other users' interests remain
- [X] T026 [P] [US4] Add unit tests in `tests/unit/test_interest_service.py` for `release_interest` (returns `True`/`False`, does not commit — a rollback restores the row, only the caller's row is affected)

### Implementation for User Story 4

- [X] T027 [US4] Add `release_interest(db, user_id, job_id) -> bool` to `jobs/interest_service.py` with a docstring stating it never commits or rolls back, so callers (the future Application Journal) own the transaction, and that a missing interest returns `False` instead of raising; reuse the scoped delete from `remove_interest`

**Checkpoint**: Release semantics are proven without implementing any application, status, recruiter, or history behavior.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Regression, style, performance, and documentation checks across all stories.

- [X] T028 Run focused tests: `.\.venv\Scripts\python.exe -m pytest tests\contract\test_interest_contract.py tests\contract\test_job_contract.py tests\contract\test_normalized_jobs_contract.py tests\integration\test_interest_workflow.py tests\integration\test_job_normalization.py tests\integration\test_migrations.py tests\unit\test_interest_service.py -q`
- [X] T029 Run the full suite and `.\.venv\Scripts\python.exe -m ruff check .` and confirm results match the T001 baseline with no new failures
- [X] T030 Verify the migration on a throwaway SQLite database: `alembic upgrade head`, then `alembic downgrade -1`, then `alembic upgrade head`, confirming the `ix_job_interests_user_created` index appears and disappears as expected
- [X] T031 Measure listing latency against a synthetic user with 10,000 interests (unfiltered and filtered) and record the percentile results and the production-load caveat in `specs/004-interest-management/quickstart.md` per SC-008
- [X] T032 Walk through the manual validation steps in `specs/004-interest-management/quickstart.md` and update `specs/004-interest-management/contracts/api-v1.md` if any observable behavior differs from the implementation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Phase 1; T002 → T003 (index name must match); T005 blocks T007 and every story phase. T004 blocks T012.
- **User Stories (Phases 3–6)**: All depend on Phase 2.
- **Polish (Phase 7)**: Depends on all desired stories.

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2; independent of other stories (seeds interests directly). MVP.
- **US2 (P1)**: Starts after Phase 2; independent of US1 for behavior, though its contract tests verify removal through the list endpoint, so T013 is easiest after T012.
- **US3 (P1)**: Starts after Phase 2; its contract update (T022) uses the list endpoint, so it follows T012.
- **US4 (P2)**: Starts after Phase 2; shares the scoped delete with T017, so it follows T017.

### Within Each Story

- Write the story's tests first and see them fail, then implement.
- Service changes (`jobs/interest_service.py`) precede route changes (`jobs/job_normalizer.py`).
- `jobs/job_normalizer.py` tasks are sequential across stories (T012, T018, T019, T020, T023, T024) because they edit one file.

### Parallel Opportunities

- Phase 2: T003, T004 in parallel after T002; T006 and T007 in parallel with each other once T003 and T005 are done.
- Phase 3: T008, T009, T010 (three different test files).
- Phase 4: T013, T014, T015, T016 (four different test files).
- Phase 5: T021 and T022; Phase 6: T025 and T026.
- Tests in `tests/unit/test_interest_service.py`, `tests/contract/test_interest_contract.py`, and `tests/integration/test_interest_workflow.py` are extended across stories; edits to the same file by different tasks must be sequential.

## Parallel Execution Example

### User Story 1

```text
Task: T008 list contract tests        -> tests/contract/test_interest_contract.py
Task: T009 list service unit tests    -> tests/unit/test_interest_service.py
Task: T010 DB-side paging test        -> tests/integration/test_interest_workflow.py
(then T011 -> T012 sequentially)
```

### User Story 2

```text
Task: T013 add/remove contract tests  -> tests/contract/test_interest_contract.py
Task: T014 remove unit tests          -> tests/unit/test_interest_service.py
Task: T015 duplicate/race tests       -> tests/integration/test_interest_workflow.py
Task: T016 job-delete interest test   -> tests/contract/test_job_contract.py
(then T017 -> T018 -> T019 -> T020 sequentially)
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phases 1–2 (baseline, index migration, schemas, service foundation).
2. Complete Phase 3 (listing with filters, sorting, pagination).
3. Stop and validate: listing is isolated, ordered, paginated in the database, and 003 is unaffected.

### Incremental Delivery

1. Foundation → US1 (list) → verify.
2. Add US2 (add/remove, job-delete cleanup) → verify.
3. Add US3 (automatic creation, atomic with normalization) → verify.
4. Add US4 (journal release capability) → verify.
5. Run Phase 7 before considering the feature complete.

## Notes

- Every task has a checkbox, sequential ID, story label for story phases, and a specific file path.
- No new technology, table, or column is introduced; one index migration is added.
- The Application Journal itself, application status, recruiter information, contact dates, status history, and any "My Jobs" aggregation are out of scope.
- Commit after each logical group if required by the repository workflow.
