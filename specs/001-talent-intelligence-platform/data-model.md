# Data Model: Talent Intelligence Platform

## Entity Relationships

```text
User 1--1 UserProfileVersion
User 1--* ProfileSession 1--* UserFile 1--* ProfileFragment
User 1--* JobInterest *--1 Job
User 1--* MatchReport 1--* MatchResult *--1 Job
User 1--* CVRequest 1--* TailoredCV
```

## Entities

### User

`id`, unique `email`, `hashed_password`, `role`, and `created_at`. Owns every private resource. Roles are standard user and administrator.

### ProfileSession and UserFile

`ProfileSession`: `id`, `user_id`, `status`, timestamps, and safe error message. It groups files for one profile-building request. States are `created -> processing -> completed` or `failed`.

`UserFile`: `id`, `user_id`, `session_id`, `blob_path`, name, content type, size, `status`, and safe error message. Permitted types are PDF, DOCX, and TXT; the default maximum is 10 MB.

### ProfileFragment and UserProfileVersion

`ProfileFragment`: `id`, `file_id`, structured extracted data, evidence metadata, source language, and timestamp. Facts carry evidence type: extracted, inferred, user-confirmed, or user-edited.

`UserProfileVersion`: `id`, `user_id`, version number, canonical profile data, output language, and timestamp. A completed merge creates a version; user-edited values override user-confirmed, extracted, and inferred values.

### Job and JobInterest

`Job`: `id`, unique `source_url`, title, employer, location, responsibilities, required and desirable qualifications and skills, technical stack, normalized details, observed timestamp, submitter ID, and status. The source URL is the deduplication key.

`JobInterest`: `user_id`, `job_id`, and timestamp, with a unique `(user_id, job_id)` constraint.

### MatchReport and MatchResult

`MatchReport` stores `id`, `user_id`, status, selected profile-version reference or snapshot, scoring-model and rules versions, timestamps, and safe error information.

`MatchResult` stores `id`, report ID, job ID and snapshot, qualitative assessments and rationale, group scores, effective weights, overall score, eligibility, rank, and completion timestamp. A completed result is immutable.

### CVRequest and TailoredCV

`CVRequest` stores `id`, `user_id`, selected match-result IDs, mode (`per_job` or `group_all`), status, timestamps, and safe error information.

`TailoredCV` stores `id`, request ID, user ID, target job or jobs, `blob_path`, and timestamp.

## Integrity Rules

- Private resources are scoped to their owning user before read, update, deletion, or download.
- Only a job submitter or administrator may delete a job.
- AI calls occur outside transactions; state changes and completed-result writes are transactional.
- Completion verifies current resource state so a retry cannot apply duplicate results.
- Failures store a client-safe message; technical diagnostics remain in protected logs.
