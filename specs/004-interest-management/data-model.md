# Data Model: Interest Management

## Existing Entity: JobInterest (table `job_interests`)

Already defined in [shared/models.py](../../shared/models.py) and created by migration `001_initial_schema`.

| Column | Type | Constraints |
|---|---|---|
| `id` | string (UUID) | Primary key |
| `user_id` | string | Not null; FK → `users.id`; indexed |
| `job_id` | string | Not null; FK → `jobs.id`; indexed |
| `created_at` | timestamp with time zone | Not null; defaults to now |

Existing uniqueness: `uq_job_interest_user_job (user_id, job_id)` (model + migration 001) and unique
index `ix_job_interests_user_job` (migration 002). Uniqueness is therefore already enforced by the
database; no new uniqueness work is needed. Interests hold no job details or application data.

## Read Model: Interest Item

Join of `job_interests` to `jobs` on `job_id`, restricted by `user_id = current user`:

| Output | Source |
|---|---|
| `id`, `jobId`, `createdAt` | `job_interests.id`, `.job_id`, `.created_at` |
| `job.id`, `title`, `company`, `location`, `url`, `source`, `postingDate` | `jobs.id`, `.title`, `.company`, `.location`, `.url`, `.source`, `.posting_date` |

Filters (`ILIKE '%…%'` with escaped wildcards) apply to `jobs.title/company/location`. Count and page
queries share the same predicate. Order: `job_interests.created_at DESC, job_interests.id DESC`.
Pagination offset/limit and the count are executed by the database.

## Required Schema Changes

1. **Composite index for the list query** (new migration `008_interest_listing_index`, revision id
   ≤ 32 characters, `down_revision = "007_job_additionals"`):
   `ix_job_interests_user_created (user_id, created_at, id)` supports the owner-scoped, newest-first,
   stable-paged query (scanned backward for descending order). Downgrade drops it.
2. **Job deletion safety** (decided in [research.md](./research.md) R10): `job_interests.job_id` has no
   `ON DELETE` rule, so the job-deletion operation explicitly deletes the job's interests in the same
   transaction. The foreign key is left unchanged.
3. Also mirror the index in the `JobInterest` model's `__table_args__` so `create_all` (tests) matches
   the migrated schema.
4. No new tables, columns, or technologies.

Migration requirements: reversible (`upgrade`/`downgrade`), runnable on SQLite (tests) and PostgreSQL
(production), covered by the existing migration test pattern, and non-destructive to existing rows.

## State and Transaction Rules

| Operation | Transaction boundary |
|---|---|
| Add interest | Select first, then insert; on unique violation roll back and return the existing row |
| Remove interest | Delete the caller's `(user_id, job_id)` row only |
| Normalization success | One commit: job fields + `status = completed`, processing job `done`, interest insert (skip if present) |
| Normalization failure (including interest write failure) | Roll back, then existing failure path: job and processing job `failed` |
| Existing normalized job resubmitted | Idempotent interest insert before responding |
| Journal entry creation | Journal insert + interest delete in the caller's single transaction; no commit inside interest code |

## Security Rules

- `user_id` is always taken from the authenticated user, never from request input.
- Queries and deletes always include `user_id = current user`; other users' rows are never matched, and
  a miss is reported as not found.
- No new roles; administrators receive no special access to other users' interests.
