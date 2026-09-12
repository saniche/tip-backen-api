# Data Model: Structured AI Processing

## Provider Request Configuration

| Field | Description | Validation |
|-------|-------------|------------|
| operation | `profile_builder`, `job_normalizer`, `job_matching`, or `cv_tailoring` | Required; selects prompt and configured model |
| model | Provider model identifier | Required; supports strict structured output |
| system instruction | Task-specific extraction/generation instruction | Required; source input cannot override it |
| user context | Candidate document, job posting, or validated upstream context | Required; never logged verbatim |
| output schema | Pydantic-derived response schema | Object root; all fields required; extras forbidden |

## Structured Profile Output

The provider result adapts to `pipeline.profile_builder.UserProfile` and its stored JSON.

| Field group | Fields | Rules |
|-------------|--------|-------|
| Identity | name, email, phone, location, LinkedIn | Required nullable strings; only source-supported values |
| Summary/preferences | summary, soft skills, languages, preferred titles/locations | Collections default empty; summary is source-grounded |
| Experience | company, title, start/end dates, summary | Complete typed entries; unavailable fields are null |
| Education | institution, degree, field, year | Complete typed entries; unavailable fields are null |
| Certifications | name, issuer, year | Complete typed entries; non-empty name required |
| Technical skills | name, level | Non-empty name; existing level vocabulary |
| Experience total | total years | Non-negative integer; no unsupported inference |

## Structured Job Output

The provider result adapts to fields populated by `normalize_job_content`.

| Field | Rules |
|-------|-------|
| key responsibilities | Required list of supported statements; empty when absent |
| required qualifications and skills | Required string lists; empty when absent |
| desirable qualifications and skills | Required string lists; empty when absent |
| technical stack | Required string list; empty when absent |

Submitted title and source metadata remain authoritative.

## Structured Match Output

The provider result adapts to `pipeline.llm_matching.LlmMatchOutput`, then existing scoring and
`JobMatchingResult.llm_match_output`.

| Field | Rules |
|-------|-------|
| Requirement groups | Required assessment lists for required/desirable qualifications and skills plus technical stack |
| Assessment | Contains `value`, `result`, `rationale`; result is `Yes`, `Partial`, or `No` |
| Notes | Required grounded explanation string |

An assessment's value corresponds to the requirement under evaluation. Scoring consumes only
validated result values.

## Structured Tailored CV Output

The provider result adapts to `pipeline.cv_tailoring.TailoredCv` before rendering and publication.

| Field | Rules |
|-------|-------|
| target role | Required string derived from selected job context |
| summary | Required string grounded in profile, job, and match context |
| experience, education, certifications | Required lists containing profile-supported statements |
| skills | Required list drawn from profile or selected job context |

## State Transitions

| Activity | Start | Success | Failure |
|----------|-------|---------|---------|
| Profile build | `created` -> `processing` | session/file `completed`; job `done`; append profile | session/job `failed`; prior profile unchanged |
| Job normalize | `pending` -> `processing` | job `completed`; job tracker `done` | tracker `failed`; job not completed |
| Match report | no report persisted | validate all results, then persist and commit | safe response; no report or result persists |
| CV tailor | request `processing`; tracker `pending` -> `running` | request/tracker complete; publish record | request/tracker fail; no record/blob published |