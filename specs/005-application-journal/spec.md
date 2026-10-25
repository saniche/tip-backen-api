# Feature Specification: Application Journal

**Feature Branch**: `005-application-journal`

**Created**: 2026-10-23

**Status**: Approved for implementation

**Input**: User description: "Allow authenticated users to track their job applications, recruiter interactions, follow-ups, notes, work authorization discussions, current status, and status-change history."

## Existing System Findings

- The service has authenticated users and a shared, normalized job catalog. Jobs contain the current
  title, company, location, source URL, source, and posting date.
- Interest Management stores a unique interest per user/job and exposes
  `release_interest(db, user_id, job_id)`, a scoped deletion operation that does not commit.
- There is no application journal or recruiter entity. Existing API conventions use FastAPI,
  Pydantic request/response models, SQLAlchemy, Alembic, standard error envelopes, and
  `page`/`limit` pagination.
- Interest Management explicitly leaves application tracking out of scope and defines the
  transactional release seam this feature must use.

## User Scenarios & Testing

### User Story 1 - Start Tracking an Application (Priority: P1)

As an authenticated job seeker, I want to start an application journal entry for a normalized job,
so that I can track progress and keep all application details together.

**Why this priority**: This creates the core record that every other journal action depends on.

**Independent Test**: Create a journal entry for a normalized job with and without a matching
interest; verify one owned entry and its initial `NotStarted` status history exist, and any matching
interest is removed.

**Acceptance Scenarios**:

1. **Given** an existing normalized job and no current interest, **When** the user creates an entry,
   **Then** the entry is created with `NotStarted`, an initial history item of `NotStarted`, and
   current job header data.
2. **Given** the user has an interest in that job, **When** the user creates an entry, **Then** the
   entry and interest removal commit together.
3. **Given** either the journal insert or interest removal fails, **When** creation is attempted,
   **Then** neither change is committed.
4. **Given** the user already has an entry for the job, **When** they create another one, **Then**
   the request returns a conflict and leaves the existing entry and interest state unchanged.
5. **Given** a job is missing or not successfully normalized, **When** the user creates an entry,
   **Then** creation is rejected and no journal or interest data changes.

### User Story 2 - Review My Application Journal (Priority: P1)

As an authenticated job seeker, I want to list and retrieve only my journal entries with their job
headers and complete history, so that I can review applications without seeing another user's
private information.

**Why this priority**: Users need to reliably find and inspect what they are tracking.

**Independent Test**: Seed entries for multiple users and jobs, list and retrieve as one user, and
verify ownership, header projection, filters, ordering, and pagination.

**Acceptance Scenarios**:

1. **Given** the user has entries, **When** they list without query parameters, **Then** the newest
   entry appears first, at most 20 records are returned, and each includes current job header
   information and chronologically ordered history.
2. **Given** matching title, company, and location filters, **When** the user supplies multiple
   filters, **Then** all filters apply together and only matching owned entries are returned.
3. **Given** more than one page of matching entries, **When** the user requests another page, **Then**
   filtering and stable ordering occur before pagination and the response contains accurate
   pagination metadata.
4. **Given** an entry belongs to another user, **When** the caller retrieves it by identifier,
   **Then** the response is not found and does not disclose the entry.
5. **Given** a job's current header information changes, **When** the user retrieves its journal
   entry, **Then** the response reflects the current normalized job fields without duplicating them
   into the journal.

### User Story 3 - Maintain Application Details (Priority: P2)

As an authenticated job seeker, I want to update recruiter information, contact and follow-up dates,
work authorization discussions, and notes without changing status history, so that the journal
stays useful as I learn more.

**Why this priority**: Keeping application details current supports the tracking workflow after
creation.

**Independent Test**: Update editable fields and verify the stored values change while status and
history remain identical.

**Acceptance Scenarios**:

1. **Given** an owned entry, **When** the user partially updates editable fields, **Then** only
   supplied fields change and status history does not change.
2. **Given** a payload contains `status`, `history`, `userId`, or `jobId` as editable fields,
   **When** the update is validated, **Then** the request is rejected.
3. **Given** the entry belongs to another user, **When** they attempt to update it, **Then** the
   response is not found and no data changes.
4. **Given** invalid recruiter or date field values, **When** submitted, **Then** standard request
   validation rejects them without changing the record.

### User Story 4 - Record Status Progress (Priority: P1)

As an authenticated job seeker, I want to update an application's status with an optional note, so
that I can see the current state and retain an auditable timeline of progress.

**Why this priority**: Status and history are central to the journal's purpose.

**Independent Test**: Change status, query current state and history, repeat the same status, then
verify exactly one history item was appended and the history remains chronological.

**Acceptance Scenarios**:

1. **Given** an owned entry, **When** the user changes status to one of the supported values,
   **Then** current status and one timestamped history item update atomically.
2. **Given** a status value is unsupported, **When** the user submits it, **Then** validation rejects
   it without modifying status or history.
3. **Given** the requested status equals the current status, **When** submitted, **Then** the
   current status remains unchanged and no history item is appended.
4. **Given** a history item already exists, **When** an ordinary journal update is made, **Then**
   that history item cannot be edited or deleted.
5. **Given** a status update fails while persisting history, **When** the operation rolls back,
   **Then** neither the current status nor history changes.

### User Story 5 - Remove an Application Entry (Priority: P3)

As an authenticated job seeker, I want to delete an application entry I no longer need, so that I
can keep my journal curated.

**Why this priority**: Deletion is useful cleanup but is not required for tracking active
applications.

**Independent Test**: Delete an owned entry and verify the journal and its history are gone, the
normalized job remains, and no interest is recreated.

**Acceptance Scenarios**:

1. **Given** an owned entry, **When** the user deletes it, **Then** its journal/history data is
   removed and the normalized job is unchanged.
2. **Given** the entry belongs to another user or does not exist, **When** deletion is attempted,
   **Then** the response is not found and no other user's data is changed.
3. **Given** an entry is deleted, **When** the user lists interests, **Then** no interest is
   automatically recreated.

### Edge Cases

- The user creates an entry for a normalized job without having an interest.
- The same user concurrently creates duplicate entries for the same job; the database uniqueness
  constraint remains authoritative and only one entry is committed.
- An interest is absent at creation or disappears before release; this is a valid no-op.
- No entries match filters, or a requested page is beyond the last page; return an empty page with
  accurate totals.
- Creation timestamps or history timestamps are equal; stable identifier ordering keeps result
  order deterministic.
- Nullable contact date, follow-up date, recruiter information, notes, and nullable job-header
  values are handled without inventing data.
- A user changes status to its current value while supplying a note; the operation does not create
  a redundant history record or modify prior history.

## Requirements

### Functional Requirements

- **FR-001**: The service MUST allow only authenticated users to create, list, retrieve, update, or
  delete their own journal entries.
- **FR-002**: Each journal entry MUST refer to one existing, successfully normalized shared job and
  one authenticated owner, without copying job header information into the entry.
- **FR-003**: The service MUST prevent more than one journal entry for the same owner and job.
- **FR-004**: A new entry MUST start with status `NotStarted` and a matching initial history item.
- **FR-005**: The supported statuses MUST be exactly `NotStarted`, `Registered`, `Applied`,
  `Contacted`, `Screening`, `Interview`, `OnHold`, and `Closed`.
- **FR-006**: Every actual status change MUST append a timestamped history item with the new status
  and optional note, and update current status as one atomic operation.
- **FR-007**: An unchanged status MUST NOT append a history item.
- **FR-008**: History items MUST be returned in chronological order, MUST be retained across status
  changes, and MUST NOT be editable or deletable through ordinary journal updates.
- **FR-009**: Ordinary partial updates MUST support recruiter information (`name`, `email`, `phone`),
  nullable contact and follow-up dates, work authorization discussion, and nullable notes. These
  updates MUST NOT create history entries.
- **FR-010**: Entry creation MUST atomically remove the matching interest when one exists, through
  the Interest Management release capability. An absent interest MUST NOT prevent creation.
- **FR-011**: If journal creation or optional interest removal fails, neither change MUST be
  committed.
- **FR-012**: The service MUST list and retrieve only the caller's entries, including current
  normalized job header fields (`id`, `title`, `company`, `location`, `url`, `source`,
  `postingDate`) and status history.
- **FR-013**: Journal listing MUST support optional case-insensitive partial filters for job
  company, title, and location. Supplied filters MUST combine with AND semantics.
- **FR-014**: Journal listing MUST sort by entry creation time descending and a stable secondary
  identifier sort, then paginate in the database.
- **FR-015**: Journal listing MUST default to page 1 and 20 entries per page, accept a maximum
  page size of 100, and return current page, page size, total matching entries, and total pages
  using the established `page`/`limit` response vocabulary.
- **FR-016**: The service MUST support deletion of an owned journal entry without deleting the
  normalized job or recreating an interest.
- **FR-017**: User-supplied owner identifiers, job headers, and status history MUST NOT be accepted
  as editable journal fields.
- **FR-018**: Invalid jobs, duplicate entries, invalid statuses, invalid field values, and
  unauthorized ownership access MUST produce the service's standard validation, conflict, or
  not-found responses as appropriate.

### Key Entities

- **Application Journal Entry**: One user's tracking record for one normalized job. It contains
  recruiter information, contact/follow-up dates, work authorization discussion, notes, current
  status, and creation/update timestamps.
- **Application Status History**: An immutable chronological record of each entry's initial status
  and each subsequent actual status change, with timestamp and optional note.
- **Normalized Job**: The existing shared job catalog record. Journal responses project its current
  header; the journal does not own or copy it.
- **User**: The existing authenticated account that owns a journal entry.
- **Job Interest**: Existing optional pre-application record; it is removed atomically when the
  corresponding journal entry is created.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In cross-user acceptance tests, 100% of list, retrieve, update, and delete operations
  expose or affect only the authenticated user's journal entries.
- **SC-002**: Every newly created journal entry has exactly one initial history entry whose status
  equals the current status.
- **SC-003**: After every successful status change, the newest history status equals the current
  status; a repeated status change creates zero additional history entries.
- **SC-004**: In all tested create failure scenarios, journal creation and matching-interest removal
  either both persist or neither persists.
- **SC-005**: Listing tests return all matching entries exactly once across pages, in stable
  newest-first order, with totals and page metadata matching the complete filtered set.
- **SC-006**: An entry's response includes current job header values while no job header fields are
  duplicated in journal storage.
- **SC-007**: Updating non-status fields creates zero status history entries.
- **SC-008**: Deleting an entry leaves its normalized job available and does not recreate an
  interest.

## Assumptions

- Existing bearer authentication and owner-scoped data access are reused; admins do not gain
  cross-user journal access.
- Only successfully normalized jobs (`status == "completed"`) are eligible for a new journal entry.
- The initial status is not client-selectable in v1; it is always `NotStarted`.
- `recruiterInfo` is an optional structured JSON object with optional `name`, `email`, and `phone`
  values, as clarified by the user. No standalone recruiter entity is introduced.
- Contact and follow-up dates are date-only values. History dates are timezone-aware timestamps.
- Deletion is supported because existing product conventions provide delete operations for
  user-owned interests and jobs.
- List pagination follows Interest Management's `page` and `limit` parameters, defaults (1, 20),
  and maximum limit (100).
- Interest Management owns interest records; this feature only calls its existing transactional
  release operation and does not otherwise change interest behavior.

## Scope Boundaries

- This feature does not provide a combined "My Jobs" aggregation endpoint.
- This feature does not create or alter jobs and does not store copied job header information.
- This feature does not implement interest creation, re-creation, or general Interest Management
  responsibilities.
- This feature does not enforce a status-transition graph; any supported status may follow any
  other supported status.
- This feature does not provide direct history edit/delete operations.
