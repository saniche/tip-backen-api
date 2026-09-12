---
description: "Task list for structured AI processing implementation"
---

# Tasks: Structured AI Processing

**Input**: Design documents from `/specs/002-structured-ai-processing/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/api-v1.md](contracts/api-v1.md)

**Tests**: Automated tests are required by FR-014 and the project constitution. Provider calls are mocked in the normal test suite.

**Organization**: Tasks are grouped by user story so that each increment can be implemented and tested independently after foundational work completes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks in its phase that modify different files.
- **[Story]**: User story served by the task. Foundational and polish tasks have no story label.

## Phase 1: Setup

**Purpose**: Establish provider configuration and test dependencies without committing credentials.

- [x] T001 Add four documented, secret-free OpenAI model configuration variables and local configuration defaults in `config.py` and `README.md`
- [x] T002 [P] Add sanitized typed provider-output fixtures for profile, job, matching, and CV scenarios in `tests/fixtures/structured_ai.py`

---

## Phase 2: Foundational Provider Boundary

**Purpose**: Provide the shared strict-schema OpenAI boundary required by every user story.

- [x] T003 Add safe provider exception types, missing-key validation, per-operation model selection, timeout handling, and metadata-only diagnostics in `llm_structured.py`
- [x] T004 Add safe translation for the new provider exceptions without exposing provider or candidate details in `errors.py`
- [x] T005 Add unit coverage for strict-schema request construction, typed success, timeout, invalid response, and safe failure translation in `tests/unit/test_llm_structured.py`

**Checkpoint**: Shared helper can return a typed Pydantic result or raise a safe local exception, with no live provider dependency in tests.

---

## Phase 3: User Story 1 - Build a Reliable Candidate Profile (Priority: P1)

**Goal**: Convert an uploaded resume into a validated, source-grounded canonical profile.

**Independent Test**: Mock a typed profile response, upload a resume, and confirm the resulting profile is populated; mock provider failure and confirm the job fails without replacing the prior profile.

- [x] T006 [P] [US1] Add strict profile output Pydantic models and conversion into existing profile dataclasses in `pipeline/profile_builder.py`
- [x] T007 [US1] Replace heuristic profile extraction with an awaited OpenAI structured call and source-grounding validation in `pipeline/profile_builder.py`
- [x] T008 [US1] Await asynchronous profile extraction and mark session, file, and processing job failures safely in `profile_builder_router.py`
- [x] T009 [US1] Add unit tests for profile typed-result conversion, null/empty fields, invalid output, and unsupported-fact rejection in `tests/unit/test_profile_builder.py`
- [x] T010 [US1] Add integration tests for successful uploaded-profile processing, provider failure state, and prior-profile preservation in `tests/integration/test_profile_processing.py`

**Checkpoint**: User Story 1 is independently usable through the existing profile-session endpoints.

---

## Phase 4: User Story 2 - Structure a Job Posting for Matching (Priority: P1)

**Goal**: Convert an unstructured posting into validated requirements and responsibilities for matching.

**Independent Test**: Mock a typed job response, normalize a posting, and confirm all requirement groups are populated; mock invalid output and confirm the job is never marked completed.

- [x] T011 [P] [US2] Add strict job-normalization Pydantic models and conversion to existing job field dictionaries in `job_service.py`
- [x] T012 [US2] Replace regex-based normalization with an awaited OpenAI structured call and required-group validation in `job_service.py`
- [x] T013 [US2] Await asynchronous normalization and preserve safe processing-job failure behavior in `job_normalizer.py`
- [x] T014 [US2] Add unit tests for job typed-result conversion, empty optional groups, and invalid output rejection in `tests/unit/test_job_service.py`
- [x] T015 [US2] Add integration tests for successful normalization, provider failure state, and non-publication of malformed results in `tests/integration/test_job_normalization.py`

**Checkpoint**: User Story 2 is independently usable through the existing job-normalization endpoint.

---

## Phase 5: User Story 3 - Receive Explainable Structured Match Results (Priority: P2)

**Goal**: Assess each job requirement with validated structured evidence and derive the existing score and eligibility result.

**Independent Test**: Mock a matching result with matched and missing requirements, create a report, and verify score/explanation persistence; mock failure and verify no report or result is created.

- [x] T016 [P] [US3] Add strict match assessment/output Pydantic models, accepted result vocabulary, and conversion to `LlmMatchOutput` in `pipeline/llm_matching.py`
- [x] T017 [US3] Replace local keyword assessment with an awaited OpenAI structured call grounded in serialized profile and job context in `pipeline/llm_matching.py`
- [x] T018 [US3] Make report creation asynchronous, await all assessments before persistence, and prevent partial report/result commits in `matching_service.py`
- [x] T019 [US3] Await asynchronous report creation while preserving existing `/matching` and `/matching/match` contracts in `job_matching_router.py`
- [x] T020 [US3] Add unit tests for assessment conversion, scoring-compatible values, invalid result rejection, and grounded rationale handling in `tests/unit/test_job_matching_pipeline.py`
- [x] T021 [US3] Add service and route tests for successful asynchronous matching plus safe provider failure without persisted reports/results in `tests/unit/test_matching_service.py` and `tests/integration/test_matching_processing.py`

**Checkpoint**: User Story 3 is independently usable through both existing matching routes.

---

## Phase 6: User Story 4 - Generate a Tailored CV from Structured Context (Priority: P2)

**Goal**: Generate and publish a validated, source-grounded tailored CV from the selected match context.

**Independent Test**: Mock a typed tailored-CV result, request tailoring, and confirm the rendered CV is available; mock an unsupported claim or provider failure and confirm no record/blob is published.

- [x] T022 [P] [US4] Add strict tailored-CV Pydantic output model and conversion to `TailoredCv` in `pipeline/cv_tailoring.py`
- [x] T023 [US4] Replace template CV generation with an awaited OpenAI structured call and post-generation grounding validation in `pipeline/cv_tailoring.py`
- [x] T024 [US4] Await asynchronous tailored-CV generation and prevent record/blob publication after invalid output or provider failure in `cv_tailoring_router.py`
- [x] T025 [US4] Add unit tests for tailored-CV conversion, empty optional sections, and unsupported-claim rejection in `tests/unit/test_cv_service.py`
- [x] T026 [US4] Add integration tests for successful provider-backed CV processing, provider failure, and no-record/no-blob publication in `tests/integration/test_cv_processing.py`

**Checkpoint**: User Story 4 is independently usable through both existing CV tailoring routes.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Verify configuration, error safety, contract compatibility, and complete regression coverage.

- [x] T027 Update OpenAI setup, four model identifiers, timeout behavior, and mock-only test guidance in `README.md` and `specs/002-structured-ai-processing/quickstart.md`
- [x] T028 [P] Add API contract regression coverage confirming unchanged success shapes and safe service-unavailable errors in `tests/contract/test_platform_contract.py` and `tests/contract/test_matching_contract.py`
- [x] T029 Run affected suites and resolve regressions from `tests/unit/test_llm_structured.py`, `tests/integration/test_profile_processing.py`, and `tests/contract/test_platform_contract.py`

---

## Dependencies & Execution Order

```text
Phase 1 Setup
    -> Phase 2 Provider Boundary
        -> US1 Profile Builder (P1)
        -> US2 Job Normalizer (P1)
            -> US3 Job Matching (P2; requires a profile and normalized job)
                -> US4 CV Tailoring (P2; requires a completed match)
                    -> Phase 7 Polish
```

US1 and US2 can be implemented in parallel after Phase 2. US3 requires their validated output shapes; US4 requires US3's matching result.

## Parallel Execution Examples

### User Story 1

Run T006 and the fixture preparation in T002 in parallel once T003 is complete. Complete T007 and T008 in order, then T009 and T010 can proceed in parallel because they edit distinct test layers.

### User Story 2

Run T011 in parallel with any remaining US1 work after T003 is complete. Complete T012 and T013 in order, then T014 and T015 can proceed in parallel.

### User Story 3

Run T016 after the foundational helper and canonical profile/job shapes are available. T017, T018, and T019 are ordered; T020 can begin once T017 is complete, while T021 follows T018 and T019.

### User Story 4

Run T022 after matching output is available. T023 and T024 are ordered; T025 can start after T023, while T026 follows T024.

## Implementation Strategy

1. Complete setup and the shared provider boundary, with its tests, before touching any existing processing flow.
2. Deliver profile building and job normalization as the first independently useful increment.
3. Add matching only after validated profile and job adapters are stable; do not allow partial persistence.
4. Add CV tailoring last because it depends on matching context and requires a post-generation grounding guard.
5. Finish with contract checks and the focused/full regression suites.

## Task Summary

| Story                  | Tasks         | Count  |
| ---------------------- | ------------- | ------ |
| Setup and foundational | T001-T005     | 5      |
| US1 - Profile builder  | T006-T010     | 5      |
| US2 - Job normalizer   | T011-T015     | 5      |
| US3 - Job matching     | T016-T021     | 6      |
| US4 - CV tailoring     | T022-T026     | 5      |
| Polish                 | T027-T029     | 3      |
| **Total**              | **T001-T029** | **29** |

## Phase 8: Convergence

- [x] T030 Prevent incomplete tailored-CV records from being committed after generation or blob-upload failure in `cv_tailoring_router.py` and cover no-record/no-blob failure behavior in `tests/integration/test_cv_processing.py` per FR-008 and FR-010 (contradicts)
- [x] T031 Mark failed profile files and normalized jobs with terminal safe failure states, and prevent jobs that are not completed from entering matching in `profile_builder_router.py`, `job_normalizer.py`, and `matching_service.py` per FR-010, US1/AC3, and US2/AC3 (partial)
- [x] T032 Validate tailored-CV summary, experience, education, and certification claims against the supplied profile/job context before rendering in `pipeline/cv_tailoring.py` and cover unsupported claims in `tests/unit/test_cv_service.py` per FR-009 and US4/AC3 (partial)
- [x] T033 Validate each structured match assessment covers an input requirement and has a grounded rationale before scoring or persistence in `pipeline/llm_matching.py` and `tests/unit/test_job_matching_pipeline.py` per FR-006, FR-013, US3/AC1, and US3/AC2 (partial)
- [x] T034 Add mocked provider-unavailability and invalid-structured-output integration tests that assert terminal failure and no partial publication for profile, job normalization, matching, and CV tailoring in `tests/integration/test_profile_processing.py`, `tests/integration/test_job_normalization.py`, `tests/integration/test_matching_processing.py`, and `tests/integration/test_cv_processing.py` per FR-014 and Constitution II/III (partial)
- [x] T035 Add metadata-only provider operation, model, latency, and outcome diagnostics without prompts, credentials, or candidate content in `llm_structured.py` and cover redaction behavior in `tests/unit/test_llm_structured.py` per plan: observability decision (partial)

## Phase 9: Convergence

- [x] T036 Delete every blob uploaded during a failed multi-CV tailoring request before committing terminal failure state in `cv_tailoring_router.py` and cover later-item upload failure cleanup in `tests/integration/test_cv_processing.py` per FR-008, FR-010, and T030 (partial)
- [x] T037 Replace lexical tailored-CV grounding with field-level source evidence validation for summary, experience, education, and certifications in `pipeline/cv_tailoring.py` and cover unsupported combinations of source words in `tests/unit/test_cv_service.py` per FR-009 and T032 (partial)
- [x] T038 Reject duplicate match assessments and validate each rationale against the specific profile evidence for its requirement in `pipeline/llm_matching.py` and `tests/unit/test_job_matching_pipeline.py` per FR-006, FR-013, and T033 (partial)
- [x] T039 Add mocked invalid-structured-output integration coverage that verifies safe terminal failure and no partial publication for profile, job normalization, matching, and CV tailoring in `tests/integration/test_profile_processing.py`, `tests/integration/test_job_normalization.py`, `tests/integration/test_matching_processing.py`, and `tests/integration/test_cv_processing.py` per FR-014 and T034 (partial)

## Phase 10: Convergence

- [x] T040 Require `Yes` and `Partial` match assessments to cite normalized evidence that is actually present in the candidate profile, rather than accepting requirement words alone, in `pipeline/llm_matching.py` and `tests/unit/test_job_matching_pipeline.py` per FR-006, FR-013, and T038 (partial)
- [x] T041 Explicitly instruct tailored-CV generation to supply valid summary, experience, education, and certification evidence references, and assert this request guidance in `pipeline/cv_tailoring.py` and `tests/unit/test_cv_service.py` per FR-008, FR-009, and T037 (partial)

## Phase 11: Convergence

- [x] T042 Persist the complete validated profile returned by structured extraction, including contact details, experience, education, certifications, preferences, and total experience, in `profile_builder_router.py` with regression coverage per FR-001 and US1/AC1 (partial)
