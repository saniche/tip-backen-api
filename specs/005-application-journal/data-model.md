# Data Model: Application Journal

## Existing entities reused

### User (`users`)

Existing account entity. Each journal entry has a required `user_id` foreign key. The owner is
always taken from the authenticated principal, not the request.

### Job (`jobs`)

Existing shared normalized job. Journal entries reference its primary key. List and detail responses
join the current record to project `id`, `title`, `company`, `location`, `url`, `source`, and
`posting_date` as `postingDate`. The header is never copied into a journal record.

### JobInterest (`job_interests`)

Existing unique `(user_id, job_id)` interest. Creation calls
`jobs.interest_service.release_interest(db, user_id, job_id)` in the same unit of work as the
journal insert. The helper scopes deletion to the owner/job pair, returns `False` when absent, and
does not commit or roll back.

## New entities

### ApplicationJournal (`application_journals`)

| Field | Type | Constraints / behavior |
|---|---|---|
| `id` | string UUID | Primary key |
| `user_id` | string | Required FK to `users.id`; indexed |
| `job_id` | string | Required FK to `jobs.id`; indexed |
| `recruiter_info` | JSON object, nullable | Optional object with optional `name`, `email`, `phone`; validated at API boundary |
| `contact_date` | date, nullable | Contact date, no time component |
| `follow_up_date` | date, nullable | Planned follow-up date, no time component |
| `work_authorization_discussed` | boolean | Required; defaults to `false` |
| `notes` | text, nullable | User-maintained notes |
| `status` | application status | Required; defaults to `NotStarted` |
| `created_at` | timestamp with timezone | Required; defaults to current UTC time |
| `updated_at` | timestamp with timezone | Required; updated on editable field/status change |

Database constraint: unique `(user_id, job_id)` named `uq_application_journal_user_job`.
Listing index: `(user_id, created_at, id)` named `ix_application_journals_user_created`, enabling
owner-scoped newest-first stable pagination.

The job reference is eligible only when `jobs.status = 'completed'`; this is a service validation
rule. The foreign key does not cascade into the shared job catalog.

### ApplicationStatusHistory (`application_status_history`)

| Field | Type | Constraints / behavior |
|---|---|---|
| `id` | string UUID | Primary key and stable ordering tie-break |
| `application_id` | string | Required FK to `application_journals.id`; cascade delete from journal |
| `date` | timestamp with timezone | Required status-event timestamp |
| `note` | text, nullable | Optional explanation/comment |
| `status` | application status | Required status for this event |

History index: `(application_id, date, id)` named `ix_application_status_history_entry_date`.
The application service only inserts history events; no ordinary update contract accepts history.
Deleting the parent journal may cascade its own history records.

## Application status values

| API value | Meaning |
|---|---|
| `NotStarted` | Created but not yet submitted |
| `Registered` | User registered/applied through an account flow |
| `Applied` | Application submitted |
| `Contacted` | Recruiter/employer contact occurred |
| `Screening` | Screening stage |
| `Interview` | Interview stage |
| `OnHold` | Process paused |
| `Closed` | Process closed |

No transition graph is imposed. Every value can follow any other value. API serialization uses
these exact values.

## Relationships and invariants

- User `1 -> many` ApplicationJournal.
- Job `1 -> many` ApplicationJournal, with only one journal per user/job.
- ApplicationJournal `1 -> many` ApplicationStatusHistory.
- Each journal creation inserts the journal plus exactly one initial history record with matching
  status in the same transaction.
- A status change updates journal status and inserts its history event in one transaction.
- After every successful operation, the current status equals the newest history status.
- A repeated status value does not insert an event.
- Updating recruiter info, dates, work authorization, or notes does not touch history.
- Entry creation and release of an optional matching interest share one transaction.
- All public journal reads and mutations include authenticated `user_id` ownership.

## Migration requirements

- Add reversible Alembic migration `009_application_journal` with `down_revision =
  "008_interest_listing_index"`.
- Create the journal and status-history tables, foreign keys, unique constraint, and indexes above.
- Use SQLAlchemy/Alembic-supported JSON, date, timezone-aware timestamp, boolean, string, and text
  types supported by both SQLite tests and PostgreSQL production.
- Keep foreign-key behavior directed from history to journal; deleting a journal may remove its
  history, but deleting a journal must not delete its job or user.
- Do not alter or backfill existing job/user/interest rows. The migration is additive and reversible.
- Mirror constraints and indexes in ORM model metadata so `Base.metadata.create_all()` test setup
  has equivalent schema guarantees.
- Migration tests must verify upgrade, schema constraints/indexes, downgrade, and that existing
  normalized jobs/interests remain intact.

## Transaction boundaries

| Operation | Unit of work |
|---|---|
| Create journal | Validate normalized job and uniqueness; insert journal and initial history; call `release_interest`; commit once |
| Update status | Verify owner; if changed, update status and insert history; commit once |
| Update editable fields | Verify owner; apply supplied fields only; commit without history insert |
| Delete journal | Verify owner; delete journal and its history; leave job and interests untouched |

Any failure before commit rolls back the complete operation. Service helpers do not commit inside
these units of work.
