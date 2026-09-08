# Quickstart: Validate Talent Intelligence Platform

## Prerequisites

- Python 3.11+ and a PostgreSQL 15+ instance.
- Azure Blob Storage configuration and an AI provider key for integration or end-to-end tests.
- Environment values for database access, token signing, storage, and AI provider configuration.
- Test doubles for blob storage and AI interfaces when running deterministic API tests.

Install dependencies and start the service:

```powershell
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

## Focused Validation

1. Run unit tests for score conversion, missing-weight redistribution, required-skill eligibility, profile-value precedence, and processing state transitions.
2. Run contract/API tests for every route in [api-v1.md](contracts/api-v1.md), including input validation, status codes, and the common error shape.
3. Run integration tests against PostgreSQL and faked or test-configured blob and AI adapters. Confirm failed provider calls mark processing failed without leaking details.
4. Run authorization tests with two users. Verify cross-user reads, updates, deletes, and CV downloads are denied; verify a job submitter and administrator may delete the submitted job.
5. Submit the same job source URL twice and confirm only one normalized job exists. Mark the job interesting twice and confirm the interest relation remains unique.

## End-to-End Scenario

1. Register and authenticate a user.
2. Create a profile session and upload up to five permitted source documents.
3. Poll processing status until completion, then read and edit the canonical profile. Confirm the edited value remains authoritative through a subsequent consolidation.
4. Submit a job for normalization, poll its status, and retrieve the normalized job.
5. Request matching for the job, poll the report, and verify qualitative assessments, deterministic scores, eligibility, and highest-score-first ranking.
6. Request both per-job and group-all tailored CV modes. Poll completion, retrieve each owner-only record, and obtain an authorized temporary download URL.

Expected result: all operations preserve ownership, report client-safe status/error information, and generated CVs contain only canonical-profile facts relevant to the selected job context.
