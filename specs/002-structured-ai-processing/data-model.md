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
| Summary/preferences | summary, soft skills, languages, preferred titles/locations | Collections default empty; summary is source-grounded and translated to the requested output language |
| Experience | company, title, start/end dates, summary, realization descriptions | Complete typed entries; descriptions contain source-supported accomplishments; unavailable fields are null |
| Education | institution, location, degree, field, year, completed | Completion is boolean; unavailable location is null |
| Certifications | name, issuer, year | Complete typed entries; non-empty name required |
| Core competences | core competences | Source-supported list; empty when absent |
| Skills | name, level | Levels are `Expert`, `Advanced`, `Intermediate`, or `Beginner`, sorted descending; derive only from source duration and contributions; omit unsupported skills; stored under the existing `skills` key |
| Additional information | additional information | Source-supported list; empty when absent |
| Output language | user-selected session language | Defaults to English; applies to extracted human-readable content irrespective of source language |
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
| summary | Required string; the prompt requests grounding in the supplied context, but no programmatic evidence or content check is applied |
| experience | Each generated entry identifies its source work experience by index. Company and dates must exactly match that entry, including missing values; the title is unrestricted. An optional one-sentence summary is prompted from the entry's `Summary` and `RealisationDescription` alongside its descriptions, but is not independently checked for factual grounding. Descriptions require evidence from the same entry. If neither source has responsibility details, the CV retains the experience header without a summary or descriptions. Company and date claims embedded in free-text titles or summaries are not independently validated. |
| education, certifications | Required lists containing profile-supported statements |
| skills | Required list; the prompt requests skills from the profile's explicit technical or soft skills, but the skills are not programmatically checked for grounding |

Validation failures include the rejected values and are returned to the authenticated request owner
through the processing job and, for `/tailoring`, the affected document. These details may contain
profile or generated text.

The CV model receives profile and job context as JSON. Experience evidence must match a source value;
an exact Python-style `field='value'` representation is also accepted when both the field and value
match the linked profile experience. Altered or mismatched evidence remains rejected.

## State Transitions

| Activity | Start | Success | Failure |
|----------|-------|---------|---------|
| Profile build | `created` -> `processing` | session/file `completed`; job `done`; append profile | session/job `failed`; prior profile unchanged |
| Job normalize | `pending` -> `processing` | job `completed`; job tracker `done` | tracker `failed`; job not completed |
| Match report | no report persisted | validate all results, then persist and commit | safe response; no report or result persists |
| CV tailor | request `processing`; tracker `pending` -> `running` | request/tracker complete; publish record | request/tracker fail; no record/blob published |