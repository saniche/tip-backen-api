---

description: "Implementation tasks for the normalized jobs listing"
---

# Tasks: Normalized Jobs Listing

**Input**: Design documents from `specs/003-normalized-jobs-list/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/api-v1.md`, `quickstart.md`

**Tests**: Contract tests are required by the project constitution and are included in each story phase.

**Organization**: Tasks are grouped by the three user stories in `spec.md`. Since the stories extend the same route and contract test module, they are completed sequentially.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks in the same phase because files and prerequisites do not overlap.
- **[Story]**: Maps a task to its user story (US1, US2, or US3).
- Every task includes its target file path.

## Path Conventions

This is a single Python web service. Application files and tests are located in `jobs/`, `shared/`, and `tests/` at the repository root.

---

## Phase 1: Setup

**Purpose**: Project initialization and basic structure

No setup changes are required. The existing Python 3.11 environment, dependencies, router, and pytest configuration support this feature.

---

## Phase 2: Foundational

**Purpose**: Define the typed response contract used by the listing before implementing its user-facing stories.

- [X] T001 Add `NormalizedJobHeader` and `NormalizedJobsResponse` Pydantic schemas with the exact six item fields and pagination metadata in `shared/schemas.py`

**Checkpoint**: The response types are available for all normalized-listing stories; no database migration or new dependency is required.

---

## Phase 3: User Story 1 - Browse Normalized Jobs (Priority: P1) 🎯 MVP

**Goal**: Let an authenticated job seeker browse the first page of completed normalized jobs with only the specified header fields.

**Independent Test**: Request the listing without filters or pagination options and verify authentication, completed-job eligibility, the six-field item shape, default page size of 20, total count, posting-date ordering, and valid empty results.

### Tests for User Story 1

- [X] T002 [US1] Add contract tests for authenticated listing, exact item shape, completed-only results, default first page, date ordering, and empty results in `tests/contract/test_normalized_jobs_contract.py`

### Implementation for User Story 1

- [X] T003 [US1] Add `GET /normalized` to return the first 20 completed global jobs with date-aware ordering and only the six header fields in `jobs/job_normalizer.py`

**Checkpoint**: The first page is independently usable and does not change the existing `GET /api/v1/jobs` behavior.

---

## Phase 4: User Story 2 - Find Jobs by Posting Details (Priority: P1)

**Goal**: Let job seekers narrow the normalized listing by title, company, and location.

**Independent Test**: Request each filter separately and then together; verify case-insensitive substring matching, AND behavior, and an empty result when nothing matches.

### Tests for User Story 2

- [X] T004 [US2] Add contract tests for title, company, and location filters individually and together, including case-insensitive and no-match cases, in `tests/contract/test_normalized_jobs_contract.py`

### Implementation for User Story 2

- [X] T005 [US2] Add optional title, company, and location filters with case-insensitive substring and combined-match behavior in `jobs/job_normalizer.py`

**Checkpoint**: Filtered listing results contain only jobs matching every supplied filter.

---

## Phase 5: User Story 3 - Navigate Listing Pages (Priority: P2)

**Goal**: Let job seekers page through all matching jobs and select a supported page size.

**Independent Test**: Request successive pages at a smaller limit and verify stable metadata, no missing or repeated jobs, validation of page bounds, and an empty result beyond the last page.

### Tests for User Story 3

- [X] T006 [US3] Add contract tests for later pages, custom limits, total-count stability, invalid pagination values, beyond-last-page results, and stable ties in `tests/contract/test_normalized_jobs_contract.py`

### Implementation for User Story 3

- [X] T007 [US3] Add validated `page` and `limit` query parameters (defaults 1 and 20, bounds 1 and 100), filtered total count, and page slicing in `jobs/job_normalizer.py`

**Checkpoint**: All three stories are independently verifiable through the normalized listing contract.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate compatibility, style, and the stated performance outcome across the completed stories.

- [X] T008 Run focused normalized-listing and existing job contract tests plus Ruff checks for `tests/contract/test_normalized_jobs_contract.py`, `tests/contract/test_job_contract.py`, `jobs/job_normalizer.py`, and `shared/schemas.py`
- [X] T009 Measure listing latency against a 10,000-job synthetic catalog and record the percentile results and production-load caveat in `specs/003-normalized-jobs-list/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No changes are required; the repository's existing environment is used.
- **Foundational (Phase 2)**: T001 establishes response schemas and must complete before the stories.
- **User Stories (Phases 3-5)**: Complete in order because each extends the same route and contract test file: US1 → US2 → US3.
- **Polish (Phase 6)**: T008 and T009 follow all desired story work; performance validation follows functional and regression validation.

### User Story Dependencies

- **US1 (P1)**: Depends on T001; otherwise standalone and is the MVP.
- **US2 (P1)**: Depends on US1's listing route because it adds filters to that same operation.
- **US3 (P2)**: Depends on US1 and US2 because it paginates their shared filtered result set.

### Within Each User Story

- Add the story's contract tests before changing the implementation.
- Implement the route/schema behavior required by that story.
- Run the focused contract test before moving to the next story.

### Parallel Opportunities

- No implementation tasks are marked `[P]`: story tests and route changes share files, and the stories extend one another's behavior.
- After T007, the focused regression/test command in T008 can be run as a single validation batch.

## Parallel Execution Examples

### User Story 1

No parallel tasks: T002 defines the contract before T003 implements the route, and both target the same listing behavior.

### User Story 2

No parallel tasks: T004 must establish filter expectations before T005 changes the shared route and test module.

### User Story 3

No parallel tasks: T006 must establish page behavior before T007 changes the same route and test module.

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001 to define response schemas.
2. Complete T002 and T003 to deliver the authenticated default listing.
3. Stop and validate the first-page contract and existing jobs-list behavior.

### Incremental Delivery

1. Add US1 and verify the header-only default listing.
2. Add US2 and verify each filter and their combined behavior.
3. Add US3 and verify page traversal, bounds, and stable ordering.
4. Run T008 and T009 before considering the feature complete.

## Notes

- Every task has a checkbox, sequential ID, required story label where applicable, and a specific file path.
- No migration, new dependency, router registration, or separate persistence model is planned.
- Commit after each logical group if required by the repository workflow.

## Phase 7: Convergence

- [X] T010 Validate the SC-004 95th-percentile response-time target under representative concurrent service load; optimize listing selection or ordering in `jobs/job_normalizer.py` if the target is missed and record the workload and result in `specs/003-normalized-jobs-list/quickstart.md` per SC-004 (partial)
