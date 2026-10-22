# Research: Interest Management

All technical-context unknowns were resolved from the existing codebase; none required external research.

## R1 — Where interest logic and routes live

- **Decision**: Add `jobs/interest_service.py` for interest business rules (add, remove, release, listing query) and keep the HTTP routes in the existing jobs router (`jobs/job_normalizer.py`), next to the existing `POST /jobs/{job_id}/interest`.
- **Rationale**: Constitution IV requires shared rules in a reusable module. The normalization workflow, the HTTP routes, and the future Application Journal all need the same operations, so they cannot live inside route functions. Keeping routes in the jobs router preserves the `/api/v1/jobs/...` URL space and allows controlling declaration order against `GET /jobs/{job_id}`.
- **Alternatives**: A new `interests` router module (rejected: the `/jobs/interests` literal must still precede `/jobs/{job_id}`, requiring include-order coupling in `main.py`); putting logic inline in routes (rejected: not reusable by the journal or the background task).

## R2 — Route shapes

- **Decision**: `GET /api/v1/jobs/interests` (list), `DELETE /api/v1/jobs/{job_id}/interest` (remove), existing `POST /api/v1/jobs/{job_id}/interest` (add).
- **Rationale**: Mirrors the precedent set by `GET /jobs/normalized` and the existing `/interest` sub-resource; no new router prefix or versioning.
- **Alternatives**: `GET /api/v1/interests` (rejected: diverges from the existing interest route location, adds a new top-level resource).

## R3 — Atomic interest creation after normalization

- **Decision**: In `_run_job_normalization`, call the interest service for `processing_job.user_id` and the job after applying structured fields and before the single final `db.commit()` that sets `status = completed`/`DONE`. Any exception falls into the existing `except` path (rollback, job `failed`, processing job `failed`, "Job normalization failed").
- **Rationale**: One commit gives the "both or neither" guarantee required by FR-015/FR-018 with no new failure-handling code. The submitter is already recorded on `ProcessingJob.user_id`.
- **Alternatives**: Create the interest at submission (rejected: would list a job that may fail normalization, violating FR-019); separate commit after completion (rejected: job could be completed with the interest missing, violating FR-018).

## R4 — Existing job on resubmission

- **Decision**: In `normalize_job`, when the existing job's `status == "completed"`, ensure the caller's interest (commit) before returning `{"id", "status": "existing"}`. For other statuses return the current response unchanged without creating an interest.
- **Rationale**: Matches the spec assumption. A manual add is available once normalization completes. Failure propagates as a standard error response, not as success.
- **Alternatives**: Queue the interest for in-flight jobs (rejected: requires a new pending-interest concept and background coordination; out of proportion for the requirement).

## R5 — Duplicate prevention and concurrency

- **Decision**: Keep the existing `uq_job_interest_user_job` constraint and unique index as the authority. The service selects first, then inserts and flushes. The HTTP add route catches `IntegrityError`, rolls back, and returns the existing interest as `status: "existing"`. No savepoints.
- **Rationale**: SQLite (tests) with pysqlite has unreliable SAVEPOINT behavior, and the completion path cannot race in practice: the add route rejects non-completed jobs (R6) and resubmission does not create interests for in-flight jobs (R4). If it ever happened, the completion path fails safely through the normal failure handling.
- **Alternatives**: Dialect-specific `INSERT ... ON CONFLICT DO NOTHING` (rejected: separate code paths per dialect for a near-impossible race).

## R6 — Eligibility on manual add

- **Decision**: 404 when the job is missing, 409 when `status != "completed"`. Jobs are a shared catalog, so any authenticated user may reference a completed job; no per-job visibility check exists or is added.
- **Rationale**: Matches spec FR-010 and the standard error codes in `main.py`. It prevents interests in jobs that cannot be shown meaningfully or matched.
- **Alternatives**: Allow any status (rejected: contradicts "existing normalized job").

## R7 — Remove semantics and ownership

- **Decision**: Delete with `WHERE user_id = :caller AND job_id = :job`; if zero rows deleted return 404 `RESOURCE_NOT_FOUND`. Admins get no extra access.
- **Rationale**: One query enforces ownership; a miss is indistinguishable for missing or foreign interests (no disclosure, FR-013/FR-014).
- **Alternatives**: 403 for foreign interests (rejected: leaks existence); idempotent 204 (rejected: spec requires 404).

## R8 — Listing query (database-side)

- **Decision**: A single SQLAlchemy 2 statement `select(JobInterest, Job).join(Job)` with `JobInterest.user_id == caller`, optional `ilike` filters on `Job.title/company/location` using the escaped contains-pattern helper from the normalized listing (extracted to a shared location), `ORDER BY JobInterest.created_at DESC, JobInterest.id DESC`, `OFFSET/LIMIT`. A second `count` statement uses the same predicates and join. `total_pages = ceil(total / limit)`, `0` when total is `0`.
- **Rationale**: Reuses 003's filter semantics and bounds (`page >= 1`, `1 <= limit <= 100`, default 20); count and page are both in the database (FR-007). Jobs are joined, so there is no per-row lookup (no N+1).
- **Alternatives**: Loading ids then jobs in Python (rejected: violates FR-007); keyset pagination (rejected: spec requires page numbers and `totalPages`).

## R9 — Index

- **Decision**: New migration `008_interest_listing_index` creating `ix_job_interests_user_created (user_id, created_at, id)`; downgrade drops it. The database scans it backward for descending order.
- **Rationale**: Supports the owner-scoped newest-first query and its stable tie-break. Existing `ix_job_interests_user_job` already serves lookups by `(user_id, job_id)`.
- **Alternatives**: Descending index columns (rejected: dialect-specific syntax in migrations for no practical gain); no index (rejected: SC-008 for 10,000 interests per user).

## R10 — Job deletion with interests

- **Decision**: Delete the job's interests explicitly inside `delete_job` before deleting the job, in the same transaction. No change to the foreign key.
- **Rationale**: Works the same on SQLite (which does not enforce foreign keys in tests) and PostgreSQL, avoids a batch-mode FK alteration migration, and is directly testable. This resolves the open planning decision in the spec checklist.
- **Alternatives**: `ON DELETE CASCADE` migration (rejected: SQLite batch table rebuild for the benefit of one code path; unobservable in the SQLite test database).

## R11 — Application Journal hook

- **Decision**: `release_interest(db, user_id, job_id) -> bool` in `jobs/interest_service.py`. It issues a scoped delete on the caller's session and never commits or rolls back. Missing interest returns `False`.
- **Rationale**: Lets the future journal call it inside its own transaction (FR-020/FR-021). Proven now with a test that wraps a simulated journal write and the release in one transaction.
- **Alternatives**: Domain events or a message queue (rejected: new architectural component, forbidden by the spec).

## R12 — Response naming

- **Decision**: camelCase for the new listing (`jobId`, `createdAt`, `postingDate`, `totalPages`) via Pydantic serialization aliases, following `NormalizedJobHeader`. Pagination envelope uses `items`, `total`, `page`, `limit`, plus `totalPages`. Existing POST add response is unchanged.
- **Rationale**: Consistent with the most recent listing contract (003); the spec's "page size" maps to the existing `limit` vocabulary.
- **Alternatives**: snake_case (rejected: inconsistent with the nearest precedent); renaming `limit` to `pageSize` (rejected: breaks convention).

## R13 — Existing test impact

- `tests/contract/test_job_contract.py::test_job_deduplication_filters_and_interest` posts an interest after normalization. It still passes (route stays `201`), but the first add now returns `status: "existing"` because normalization already created the interest. Extend rather than weaken the assertions.
