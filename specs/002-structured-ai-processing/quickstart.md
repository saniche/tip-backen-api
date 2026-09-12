# Quickstart: Validate Structured AI Processing

## Prerequisites

- Configure local database and storage settings from the repository README.
- Set `OPENAI_API_KEY` locally; do not commit it.
- Configure the four operation-specific model identifiers: `OPENAI_PROFILE_BUILDER_MODEL`,
  `OPENAI_JOB_NORMALIZER_MODEL`, `OPENAI_JOB_MATCHING_MODEL`, and
  `OPENAI_CV_TAILORING_MODEL`. They default to `gpt-4o-mini`; optionally set
  `OPENAI_TIMEOUT_SECONDS` (default: `60`).
- Start the API from the repository root.

```powershell
alembic upgrade head
uvicorn main:app --reload
```

## Automated Validation

Provider calls must be mocked in standard tests, so they run without credentials.

```powershell
python -m pytest -q tests/unit tests/integration
```

Expected results:

- Valid typed provider responses populate existing profile, job, match, and CV data.
- Invalid output and unavailable provider cases do not publish partial data.
- Profile/job/CV failures become terminal failed jobs; matching writes no partial report.
- Tailored CV grounding tests reject unsupported claims.

## Manual End-to-End Smoke Test

1. Register and authenticate a test user with the existing Postman collection.
2. Upload a sanitized resume, poll the profile job, and verify structured skills and experience.
3. Normalize a sanitized job posting, poll its job, and verify requirements and responsibilities.
4. Create a match report and verify assessments, score, eligibility, and rationale.
5. Tailor a CV from a matching result, poll completion, and verify only supported profile/job facts.

See [data-model.md](data-model.md) for output structures and
[contracts/api-v1.md](contracts/api-v1.md) for compatibility behavior.

## Failure Smoke Test

Use an unavailable or invalid provider configuration in an isolated local environment. Matching
must return a safe service-unavailable error; profile, job, and CV processing must become `failed`
without replacing earlier successful records. Restore configuration afterward.
