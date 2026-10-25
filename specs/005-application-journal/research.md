# Research: Application Journal

All implementation choices were resolved from the user requirements and existing repository
conventions; no external technology or dependency is needed.

## R1 — API resource and routing

- **Decision**: Add an `applications` router mounted under `/api/v1`, with REST-style endpoints under
  `/applications`.
- **Rationale**: Journal entries are a distinct resource, separate from jobs and interests. The
  existing service mounts feature routers in `main.py`; this route avoids adding journal
  responsibilities to Interest Management.
- **Alternatives**: Nesting under `/jobs` was rejected because an application is a user-owned
  tracking record, not a job or interest.

## R2 — Persistence model

- **Decision**: Store application entries and status history in separate relational tables.
  Store `recruiterInfo` as a nullable JSON object, validated by a strict Pydantic model with
  optional `name`, `email`, and `phone`.
- **Rationale**: SQLAlchemy/Alembic and SQLite/PostgreSQL are already established. A separate history
  table supports append-only writes, chronological retrieval, transactional consistency, and
  parent-entry deletion. JSON is already used for structured fields in ORM models.
- **Alternatives**: Embedding history in mutable JSON was rejected because it weakens append-only
  guarantees and database-side event retrieval. A new recruiter table was rejected because no
  recruiter lifecycle or cross-application relationship is required.

## R3 — Status representation and history rules

- **Decision**: Use a string enum with the exact API values `NotStarted`, `Registered`, `Applied`,
  `Contacted`, `Screening`, `Interview`, `OnHold`, and `Closed`; persist and serialize those values.
  Insert one initial event, then append only when a status actually changes.
- **Rationale**: Matches the explicit user contract while preserving Python enum validation. The
  existing project uses `str, enum.Enum` for statuses and Pydantic serialization.
- **Alternatives**: Adding transition restrictions was rejected because requirements explicitly
  allow any supported status to follow any other. History JSON edits through the generic update
  endpoint were rejected.

## R4 — Interest Management integration and atomicity

- **Decision**: Call `jobs.interest_service.release_interest(db, user_id, job_id)` between the
  journal/history inserts and the single commit. Let the helper remain non-committing.
- **Rationale**: This is the explicit capability provided by Interest Management. Shared session
  and one commit make journal creation plus optional interest deletion atomic.
- **Alternatives**: Calling the HTTP delete endpoint or committing in the interest service was
  rejected because either would split the transaction and violate the requirement.

## R5 — Ownership and duplicate behavior

- **Decision**: Take `user_id` only from `get_current_user`; include owner predicates on every
  retrieve/update/delete. Enforce unique `(user_id, job_id)` in the database and translate duplicate
  insert conflicts to the existing 409 `CONFLICT` response.
- **Rationale**: Mirrors interest ownership rules and prevents races from bypassing an application
  pre-check.
- **Alternatives**: Admin cross-owner access or returning 403 for a foreign ID was rejected because
  it leaks record existence and is not required.

## R6 — List filters and pagination

- **Decision**: Reuse Interest Management conventions: filters `company`, `title`, `location`;
  case-insensitive literal substring matching; AND semantics; page defaults 1/20; maximum limit
  100; count and page query in SQL; `created_at DESC, id DESC`; `totalPages` in the response.
- **Rationale**: Consistent API vocabulary and behavior, while satisfying stable paginated listing
  requirements.
- **Alternatives**: Loading all rows in Python was rejected because it violates the database-side
  filtering/pagination requirement.

## R7 — Deletion and job lifecycle

- **Decision**: Support owner-scoped journal deletion. Delete history with its parent entry, but
  preserve the shared job and do not create an interest.
- **Rationale**: Existing APIs support deletion for owned resources, and the feature explicitly
  requires deletion not to affect the normalized job or re-create an interest.
- **Alternatives**: Soft deletion was rejected because no audit/retention requirement exists and
  it complicates owner-scoped uniqueness semantics.

## R8 — Migration and testing

- **Decision**: Add migration `009_application_journal` after `008_interest_listing_index`; test
  SQLite migration upgrade/downgrade using the current Alembic test pattern and exercise the same
  ORM metadata with the existing in-memory test database.
- **Rationale**: This follows the established Alembic chain and database boundary tests.
- **Alternatives**: New persistence technology or hand-managed schema changes were rejected.
