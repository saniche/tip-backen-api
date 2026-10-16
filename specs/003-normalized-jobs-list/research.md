# Research: Normalized Jobs Listing

## Existing Service Conventions

### Decision: Add a separate normalized listing route

**Rationale**: The existing `GET /api/v1/jobs` returns an unwrapped list with a different field set, default page size, and creation-date ordering. Reusing it would change an existing contract. A static `GET /api/v1/jobs/normalized` route gives the new contract a distinct surface and must be registered before the dynamic `/{job_id}` route.

**Alternatives considered**:
- Change the existing listing in place: rejected because the feature requires new behavior without changing existing behavior.
- Add a second top-level jobs router: rejected because the existing router already owns job operations and is included under `/api/v1`.

### Decision: Reuse global `Job` records and completed status

**Rationale**: `Job` is already shared across users and tracks normalization with a status field. Limiting results to `completed` excludes pending and failed processing records and avoids partial normalized data. The existing auth dependency remains required, but results are not restricted by submitter.

**Alternatives considered**:
- Add a separate listing table or per-user relation: rejected because the existing model already represents the global catalog.
- Include pending/failed jobs: rejected because they do not meet the feature's “normalized jobs” requirement.

### Decision: Return a typed page with exactly six header fields

**Rationale**: The response should give consumers a predictable, compact shape. The item fields are `id`, `title`, `company`, `location`, `postingDate`, and `source`; nullable stored fields remain nullable. A typed response avoids unconstrained item dictionaries while keeping the established `items`, `total`, `page`, and `limit` pagination vocabulary.

**Alternatives considered**:
- Return the complete normalized record: rejected by the clarification limiting output to header information.
- Return a bare list: rejected because it cannot carry total count and page metadata.

### Decision: Reuse the current query and page-size conventions

**Rationale**: Use `title`, `company`, `location`, `page`, and `limit`; page defaults to 1 and limit defaults to 20. The current list caps `limit` at 100, so retain that maximum. Text filters use case-insensitive substring matching and combine with AND semantics, consistent with current behavior.

**Alternatives considered**:
- Introduce different pagination parameter names or a new maximum: rejected to avoid an inconsistent API convention.
- Match only complete field values: rejected because the existing jobs listing supports partial text matches.

### Decision: Sort posting dates chronologically and handle invalid values explicitly

**Rationale**: The stored `posting_date` is nullable text rather than a database date type. Treat ISO 8601 date and datetime strings as valid, and use date-aware ordering to reliably place missing or unparseable values last across SQLite and PostgreSQL. Use the selected header values for ordering, then a stable `id` tie-breaker, and apply page slicing after ordering. Return the stored string unchanged.

**Alternatives considered**:
- Rely on lexicographic ordering of the stored text: rejected because non-ISO or invalid values can sort incorrectly.
- Change the database column type and migrate existing data: rejected as unnecessary schema scope for a read-only listing.

## Project Constraints

- The deployed service uses Python 3.11, FastAPI, Pydantic 2, and SQLAlchemy 2.
- Automated tests use pytest, FastAPI `TestClient`, and an in-memory SQLite database; production storage is PostgreSQL.
- No external service, migration, or new dependency is required.
- Normal-load measurement for the specification's 2-second target must use a representative catalog; implementation tests should focus on contract correctness and avoid introducing a benchmark framework.
