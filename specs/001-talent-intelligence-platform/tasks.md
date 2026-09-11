---
description: "Implementation tasks for Talent Intelligence Platform"
---

# Tasks: Talent Intelligence Platform

**Input**: Design documents from `specs/001-talent-intelligence-platform/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [api-v1.md](contracts/api-v1.md), and [quickstart.md](quickstart.md)

**Tests**: Required by the project constitution. Implement each story test-first; include unit,
contract, and integration coverage at affected boundaries.

**Organization**: Tasks are grouped by user story so each increment is independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with tasks that change different files and have no incomplete dependency.
- **[Story]**: User story ownership label for story-phase tasks.

## Phase 1: Setup

**Purpose**: Establish the test and migration tooling required before feature behavior is added.

- [x] T001 Add pytest, pytest-asyncio, and test configuration in `requirements-dev.txt` and `pyproject.toml`
- [x] T002 [P] Create unit, contract, and integration test packages in `tests/unit/__init__.py`, `tests/contract/__init__.py`, and `tests/integration/__init__.py`
- [x] T003 Configure Alembic and create the initial migration environment in `alembic.ini` and `alembic/env.py`

---

## Phase 2: Foundational

**Purpose**: Build shared API, security, asynchronous-processing, persistence, and adapter boundaries.

**Blocking**: Complete this phase before implementing any user story.

- [x] T004 Add `/api/v1` router mounting, request correlation, `/health`, and `/ready` endpoints in `main.py`
- [x] T005 Define common API error and paginated-response schemas in `schemas.py`
- [x] T006 Add centralized exception translation and safe structured logging in `main.py` and `errors.py`
- [x] T007 Extend authenticated identity with standard/admin roles and reusable ownership policies in `models.py`, `auth.py`, and `authorization.py`
- [x] T008 Create reusable processing-resource lifecycle operations and safe failure transitions in `models.py` and `processing_service.py`
- [x] T009 Isolate structured AI provider operations behind validated interfaces in `llm_structured.py`
- [x] T010 Isolate authorized file persistence and temporary-download URL generation in `storage.py`
- [x] T011 Create shared database, authenticated-client, AI-fake, and storage-fake fixtures in `tests/conftest.py`
- [x] T012 Add contract and integration coverage for API V1 error shape, token failures, ownership denial, health/readiness, and processing failure sanitization in `tests/contract/test_platform_contract.py` and `tests/integration/test_platform_boundaries.py`

**Checkpoint**: Shared dependencies can return versioned, correlated, safe errors; test fakes can replace AI and blob storage; every future route can apply authenticated ownership checks.

---

## Phase 3: User Story 1 - Build a Canonical Profile (Priority: P1)

**Goal**: An authenticated user builds, views, and edits a canonical profile from a successful document session without later processing overwriting their edits.

**Independent Test**: Upload complementary/conflicting documents, wait for completion, retrieve the consolidated profile, edit one field, then confirm a later merge preserves that edit.

- [x] T013 [P] [US1] Write profile-session state and precedence unit tests in `tests/unit/test_profile_service.py`
- [x] T014 [P] [US1] Write profile API contract tests for sessions, files, profile reads/updates, invalid files, and cross-user denial in `tests/contract/test_profile_contract.py`
- [x] T015 [P] [US1] Write profile processing integration tests with fake AI and storage adapters in `tests/integration/test_profile_processing.py`
- [x] T016 [US1] Add ProfileSession, UserFile, ProfileFragment, and versioned UserProfile persistence models and migration in `models.py` and `alembic/versions/001_profile_processing.py`
- [x] T017 [US1] Add profile session, upload, profile update, and profile response schemas in `schemas.py`
- [x] T018 [US1] Implement extraction, evidence recording, completion checks, consolidation, and user-edited value precedence in `profile_service.py`
- [x] T019 [US1] Implement background profile processing with permitted PDF/DOCX/TXT and configurable size validation in `profile_builder_router.py`
- [x] T020 [US1] Replace the preliminary profile-builder routes with `/api/v1/profile` session, file, status, read, and update routes in `profile_builder_router.py`
- [x] T021 [US1] Register the profile migration and run the focused profile unit, contract, and integration tests from `tests/unit/test_profile_service.py`, `tests/contract/test_profile_contract.py`, and `tests/integration/test_profile_processing.py`

**Checkpoint**: User Story 1 is independently usable and meets FR-002 through FR-007 and its profile-related ownership/error requirements.

---

## Phase 4: User Story 2 - Normalize and Explore Jobs (Priority: P2)

**Goal**: An authenticated user submits a job, receives normalized structured details, finds jobs through filters, and records an interest without duplicate jobs or interests.

**Independent Test**: Submit a posting, poll completion, repeat its source URL, filter the job list, and create the same interest twice while observing one job and one interest record.

- [x] T022 [P] [US2] Write job normalization and filter-ordering unit tests in `tests/unit/test_job_service.py`
- [x] T023 [P] [US2] Write job and interest API contract tests for normalization, filtering, pagination, duplicate URL, interest uniqueness, and deletion authorization in `tests/contract/test_job_contract.py`
- [x] T024 [P] [US2] Write PostgreSQL and fake-AI normalization integration tests in `tests/integration/test_job_normalization.py`
- [x] T025 [US2] Add Job submitter/status fields, JobInterest, source URL and user-job uniqueness constraints, and migration in `models.py` and `alembic/versions/002_jobs_and_interests.py`
- [x] T026 [US2] Add normalization, job-search, pagination, and interest request/response schemas in `schemas.py`
- [x] T027 [US2] Implement idempotent job normalization, validation, filtering, newest-first ordering, interests, and submitter/admin deletion policies in `job_normalizer.py`
- [x] T028 [US2] Replace preliminary job extraction routes with `/api/v1/jobs` normalization, list, detail, interest, and deletion routes in `job_normalizer.py`
- [x] T029 [US2] Run the focused job unit, contract, and integration tests from `tests/unit/test_job_service.py`, `tests/contract/test_job_contract.py`, and `tests/integration/test_job_normalization.py`

**Checkpoint**: User Story 2 is independently usable and meets FR-008 through FR-012, including shared-job deduplication and owner/admin deletion rules.

---

## Phase 5: User Story 3 - Compare Profile to Jobs (Priority: P3)

**Goal**: A user selects jobs and receives an immutable, ranked report whose final scores and eligibility are calculated deterministically by the service.

**Independent Test**: Compare a known profile against multiple jobs, verify per-requirement explanations and high-to-low ranking, then list/view/delete only the owner’s report.

- [x] T030 [P] [US3] Write deterministic score conversion, missing-weight redistribution, eligibility, and ranking unit tests in `tests/unit/test_matching_scoring.py`
- [x] T031 [P] [US3] Write match-report service tests for snapshots, unavailable jobs, missing profiles, and immutable completed results in `tests/unit/test_matching_service.py`
- [x] T032 [P] [US3] Write matching API contract tests for create, list, detail, deletion, ranking, and ownership denial in `tests/contract/test_matching_contract.py`
- [x] T033 [P] [US3] Write PostgreSQL and fake-AI matching integration tests in `tests/integration/test_matching_processing.py`
- [x] T034 [US3] Add MatchReport and MatchResult persistence fields for profile/job snapshots, rules/scoring versions, qualitative analysis, rank, and status in `models.py` and `alembic/versions/003_matching_reports.py`
- [x] T035 [US3] Add multi-job matching, report-list, report-detail, and ranked-result schemas in `schemas.py`
- [x] T036 [US3] Implement the deterministic scoring engine with base weights, proportional redistribution, and required-skill eligibility in `matching_scoring.py`
- [x] T037 [US3] Implement report creation, AI qualitative assessment validation, immutable result persistence, ranking, listing, viewing, and owner deletion in `matching_service.py` and `matching_tasks.py`
- [x] T038 [US3] Replace the preliminary one-job synchronous matcher with `/api/v1/matching` report routes in `job_matching_router.py`
- [x] T039 [US3] Run the focused matching unit, contract, and integration tests from `tests/unit/test_matching_scoring.py`, `tests/unit/test_matching_service.py`, `tests/contract/test_matching_contract.py`, and `tests/integration/test_matching_processing.py`

**Checkpoint**: User Story 3 is independently usable and meets FR-013 through FR-016 with reproducible, deterministic, owner-scoped reports.

---

## Phase 6: User Story 4 - Generate a Tailored CV (Priority: P4)

**Goal**: A user generates one CV per selected matching result or one combined CV, then views, downloads, or deletes only their own generated records.

**Independent Test**: Generate a CV for a known match, verify it is grounded in the profile and selected job context, then retrieve a temporary owner-authorized download URL.

- [x] T040 [P] [US4] Write CV mode, ownership, deleted-job, mixed-owner, and no-fabrication service tests in `tests/unit/test_cv_service.py`
- [x] T041 [P] [US4] Write CV API contract tests for per-job/group-all requests, list/detail/delete, and download authorization in `tests/contract/test_cv_contract.py`
- [x] T042 [P] [US4] Write fake-AI and fake-blob CV integration tests, including safe background failures and expiring download links, in `tests/integration/test_cv_processing.py`
- [x] T043 [US4] Add CVRequest and expanded TailoredCV ownership, selected-result, mode, status, and target-job fields with migration in `models.py` and `alembic/versions/004_tailored_cvs.py`
- [x] T044 [US4] Add CV request mode, CV metadata, view, list, and temporary-download response schemas in `schemas.py`
- [x] T045 [US4] Implement grounded tailoring validation, per-job/group-all orchestration, markdown rendering, storage persistence, owner-only retrieval, and deletion in `cv_service.py` and `cv_tasks.py`
- [x] T046 [US4] Replace the preliminary CV routes with `/api/v1/cv` create, list, view, download, and delete routes in `cv_tailoring_router.py` and `download_router.py`
- [x] T047 [US4] Run the focused CV unit, contract, and integration tests from `tests/unit/test_cv_service.py`, `tests/contract/test_cv_contract.py`, and `tests/integration/test_cv_processing.py`

**Checkpoint**: User Story 4 is independently usable and meets FR-017 through FR-020 with safe owner-only storage access.

---

## Phase 7: Polish and Cross-Cutting Concerns

**Purpose**: Validate the complete V1 flow and operational requirements without adding new product scope.

- [x] T048 [P] Add request ID, user-safe error, and secret-redaction logging coverage in `tests/integration/test_observability.py`
- [x] T049 [P] Add the complete profile-to-CV acceptance scenario in `tests/integration/test_end_to_end_platform.py`
- [x] T050 [P] Add migration-upgrade and schema-constraint coverage in `tests/integration/test_migrations.py`
- [x] T051 Document local configuration, permitted file types, environment variables, and focused test commands in `README.md` and `.env.example`
- [x] T052 Run formatting, static analysis, all pytest suites, migration upgrade, and the Docker build using `pyproject.toml`, `alembic.ini`, `tests/`, and `Dockerfile`

---

## Dependencies and Execution Order

```text
Setup (T001-T003)
        -> Foundational (T004-T012)
            -> US1 Profile (T013-T021)
                -> US2 Jobs (T022-T029)
                    -> US3 Matching (T030-T039)
                        -> US4 CV Tailoring (T040-T047)
                            -> Polish (T048-T052)
```

US1 is the MVP. US2 can start after the foundational phase, but US3 needs the profile and jobs
delivered by US1 and US2. US4 needs completed match results from US3.

## Parallel Execution Examples

- After T001, T002 and T003 can proceed in parallel.
- In US1, T013-T015 can proceed in parallel before T016-T020.
- In US2, T022-T024 can proceed in parallel before T025-T028.
- In US3, T030-T033 can proceed in parallel before T034-T038.
- In US4, T040-T042 can proceed in parallel before T043-T046.
- In polish, T048-T050 can proceed in parallel once all stories are complete.

## Implementation Strategy

1. Deliver the shared foundation and User Story 1 as the MVP: authenticated profile processing,
   safe persisted status, canonical profile retrieval, and edit precedence.
2. Add shared normalized jobs and interests, then prove duplicate suppression and search behavior.
3. Add async report processing with AI qualitative assessments and deterministic score/ranking rules.
4. Add grounded CV generation and protected temporary downloads.
5. Finish with full-flow, migration, observability, and deployment validation.

---

## Phase 8: Convergence

- [x] T053 Create and validate the missing initial Alembic migration for the implemented persistence models per plan: persistence/migrations (missing)
- [x] T054 Implement the absent provider-isolated profile, matching, CV-tailoring, and markdown adapter modules required by the existing routers per plan: provider isolation (missing)
- [x] T055 Complete document extraction, evidence tracking, successful-session merge gating, and user-edited profile precedence per FR-004, FR-005, and FR-006 (partial)
- [x] T056 Complete asynchronous job normalization with structured requirement extraction, saved-date filtering, and the planned response contract per FR-008 and FR-010 (partial)
- [x] T057 Replace the single-job synchronous matcher with owner-scoped ranked match reports supporting immutable results and list, view, and delete operations per FR-013, FR-015, and FR-016 (contradicts)
- [x] T058 Implement the `/cv` request, per-job/group-all generation, owner-scoped list/detail/delete operations, and authorized download contract per FR-017 and FR-019 (contradicts)
- [x] T059 Centralize ownership authorization, common error schemas, and provider/storage failure sanitization across externally reachable routes per FR-001 and FR-020 (partial)
- [x] T060 Add the missing focused unit, contract, integration, migration, observability, and end-to-end tests required by Constitution II, Constitution III, and T012/T048-T052 (missing)

---

## Phase 9: Convergence

- [x] T061 Preserve profile evidence metadata and user-edited precedence across subsequent successful document merges per FR-004, FR-005, and FR-006 (partial)
- [x] T062 Complete structured asynchronous job normalization, including requirements, responsibilities, saved-date filtering, pagination, and the planned response contract per FR-008 and FR-010 (partial)
- [x] T063 Implement validated match explanations, deterministic result classification, immutable profile/job context, and scoring metadata per FR-013, FR-014, and FR-015 (partial)
- [x] T064 Implement separate-job and group-all CV request modes with grounding validation and selected-job context per FR-017 and FR-018 (partial)
- [x] T065 Harden CV storage/download lifecycle and sanitize background failure details, with owner-scoped contract and integration coverage per FR-019, FR-020, and Constitution III (partial)
- [x] T066 Add the missing Alembic revisions and profile, job, matching, and CV boundary test suites required by the plan, Constitution II/III, and T015/T021/T024/T029/T032/T033/T039/T040-T047 (missing)
- [x] T067 Add observability, end-to-end, migration, configuration documentation, static-analysis, and deployment validation required by T048-T052 and SC-001/SC-002/SC-004/SC-005/SC-006 (missing)

---

## Phase 10: Convergence

- [x] T068 Implement asynchronous job normalization with a persisted processing resource, structured extraction, saved-date filtering, pagination, and the planned polling response contract per FR-008, FR-010, and plan: BackgroundTasks (partial)
- [x] T069 Add PostgreSQL/fake-AI job normalization boundary coverage and replace the no-op `002_jobs_and_interests.py` revision with substantive jobs and interests schema migration per T024/T025 and plan: PostgreSQL boundary (partial)
- [x] T070 Resolve repository-wide Ruff findings and run the Docker build in a Docker-enabled environment as required by T052 and Constitution II/III (partial)
- [x] T071 Complete the final validation matrix and reconcile residual task tracking after asynchronous normalization, static analysis, migration, and Docker validation per T060/T067 (partial)
