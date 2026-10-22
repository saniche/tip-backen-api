# Feature Specification: Interest Management

**Feature Branch**: `004-interest-management`

**Created**: 2026-10-21

**Status**: Draft

**Input**: User description: "Interest Management — allow authenticated users to manage jobs they are interested in before tracking them in the application journal: list own interests (with filtering, sorting, pagination), add and remove interests, automatically create an interest after successful job normalization, and release an interest atomically when an application journal entry is created."

## Existing System Findings

Inspection of the current codebase and specifications (001 platform, 002 structured AI processing, 003 normalized jobs listing) shows:

- A user-to-job interest record already exists (unique per user and job) and a create-only operation exists. There is **no** way to list or remove interests, and no automatic creation after normalization.
- Normalized jobs are a **shared, URL-deduplicated catalog**; submitting an already-known URL reuses the existing job.
- Normalization is accepted immediately and completed in the background; a failed normalization marks both the job and its processing record as failed.
- The normalized jobs listing (003) already defines the pagination vocabulary (`page`, `limit`, default 20, maximum 100, `total`) and filter semantics (case-insensitive partial match, AND-combined).
- **No Application Journal exists yet.** This feature defines the interest-side behavior the journal must call; it does not build the journal.

## Clarifications

### Session 2026-10-21

- Q: Should the listing's job header include the source URL? → A: Yes. The header contains `id`, `title`, `company`, `location`, `url`, `source`, and `postingDate`, read from the shared job and never copied into the interest record.
- Q: Which jobs may a user add manually? → A: Any normalized (successfully completed) job in the shared catalog; all authenticated users are authorized to reference any such job because the catalog is not user-scoped.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Review My Interests (Priority: P1)

As a job seeker, I want to see the jobs I have marked as interesting, newest first, and narrow them by company, title, or location, so that I can decide which ones to pursue.

**Why this priority**: Viewing interests is the primary value; without it, saved interests are invisible.

**Independent Test**: Seed two users with interests, list as one user, and verify only that user's interests are returned, newest first, with job header information and pagination metadata.

**Acceptance Scenarios**:

1. **Given** a user has interests, **When** they request their interests without options, **Then** the response contains at most 20 interests, most recently created first, each with its interest identifier, job identifier, creation time, and job header information (title, company, location, source URL, source, posting date where available).
2. **Given** another user also has interests, **When** the first user lists interests, **Then** none of the other user's interests appear and the total counts only the first user's interests.
3. **Given** a user has interests in jobs with different companies, titles, and locations, **When** one or more filters are supplied, **Then** only interests whose job matches every supplied filter (case-insensitive, partial match) are returned.
4. **Given** more than one page of matching interests, **When** a later page or different page size is requested, **Then** the page contains the corresponding interests, with no duplicates or omissions across pages even when creation times are equal, and the metadata reports current page, page size, total matching records, and total pages.
5. **Given** a user has no matching interests, **When** they list interests, **Then** the response is a successful empty page with a total of zero and zero total pages.
6. **Given** an invalid page or page size, **When** the user lists interests, **Then** the request is rejected with the service's standard validation error.

---

### User Story 2 - Add and Remove an Interest (Priority: P1)

As a job seeker, I want to mark an existing normalized job as an interest and remove it later, so that I can curate my shortlist without affecting the shared job catalog.

**Why this priority**: Manual curation is the core management capability alongside listing.

**Independent Test**: Add a normalized job twice and confirm one interest exists; remove it and confirm the interest is gone while the job is still retrievable.

**Acceptance Scenarios**:

1. **Given** a normalized job exists, **When** a user adds it as an interest, **Then** an interest is created for that user and job.
2. **Given** the user already has an interest in that job, **When** they add it again, **Then** no second interest is created and the response identifies the existing interest (existing behavior preserved).
3. **Given** a job identifier that does not exist, **When** a user adds it, **Then** the request fails with the standard "not found" error and nothing is created.
4. **Given** a job whose normalization has not completed successfully, **When** a user adds it, **Then** the request is rejected with the standard conflict error and nothing is created.
5. **Given** a user has an interest in a job, **When** they remove it, **Then** the interest is deleted and the normalized job remains in the catalog.
6. **Given** a user has no interest in a job (including when only another user does), **When** they attempt to remove it, **Then** the request fails with the standard "not found" error and the other user's interest is unaffected.
7. **Given** two simultaneous requests to add the same job, **When** both complete, **Then** exactly one interest exists and neither request is reported as a server failure.

---

### User Story 3 - Interest Created Automatically After Normalization (Priority: P1)

As a job seeker, I want a job I submit for normalization to be added to my interests automatically so that I do not have to mark it manually.

**Why this priority**: It is the main way interests enter the system and completes the submission workflow.

**Independent Test**: Submit a new job, wait for normalization to complete, and verify the submitter's interest list contains it exactly once; resubmit the same job and verify still exactly one.

**Acceptance Scenarios**:

1. **Given** a user submits a new job, **When** normalization and persistence succeed, **Then** the job is in that user's interests, and the job becoming "completed" and the interest being created happen together or not at all.
2. **Given** a user submits a job whose URL already exists as a normalized job, **When** the submission is accepted, **Then** the existing job is reused (no new job) and that user's interest in it is created if it does not already exist.
3. **Given** the same user resubmits the same job any number of times, **When** all submissions finish, **Then** exactly one interest exists for that user and job.
4. **Given** two different users submit the same job, **When** both finish, **Then** each user has their own single interest in the one shared job.
5. **Given** the interest cannot be created, **When** the normalization workflow finishes, **Then** the workflow is reported as failed in the same way other normalization failures are reported; the operation is never reported as successful without the interest.
6. **Given** normalization itself fails, **When** the workflow finishes, **Then** no interest is created.

---

### User Story 4 - Interest Released When an Application Is Created (Priority: P2)

As a job seeker, when I start tracking an application for a job I was interested in, I want the interest removed automatically so that the job moves out of my shortlist and into my journal.

**Why this priority**: Prevents a job appearing in two places, but depends on the Application Journal capability, which is out of scope here.

**Independent Test**: With an interest present, invoke the interest-release capability inside a unit of work that also records an application (test double); verify both outcomes commit together or roll back together.

**Acceptance Scenarios**:

1. **Given** a user has an interest in a job, **When** an application journal entry is created for that job, **Then** the interest is removed in the same atomic operation as the entry creation.
2. **Given** the journal entry creation fails, **When** the operation is rolled back, **Then** the interest still exists.
3. **Given** the interest removal fails, **When** the operation is rolled back, **Then** no journal entry is created.
4. **Given** the user has no interest in the job, **When** a journal entry is created, **Then** the creation proceeds normally and no error arises from the missing interest.
5. **Given** an interest is released because of an application, **When** the operation completes, **Then** the normalized job is not deleted and other users' interests in it are unaffected.

### Edge Cases

- A normalized job is deleted by its submitter or an administrator while users hold interests in it; the interests are removed with it so deletion does not fail or leave dangling interests.
- Filters that are blank or whitespace-only are ignored; filter text containing wildcard characters is matched literally.
- A job has null company, location, source, or posting date; the interest is still listed and the missing fields are returned as null.
- A page beyond the last page returns a successful empty page with the unchanged total.
- A submission for an existing job whose normalization is still in progress or failed does not create an interest until the job is normalized; the response reports the job's existing state (see Assumptions).
- Unauthenticated callers are rejected on every interest operation.
- Requests for another user's interest are indistinguishable from requests for a non-existent interest, so ownership is not disclosed.
- Application status, recruiter details, contact dates, and status history are never part of an interest.

## Requirements *(mandatory)*

### Functional Requirements

**Listing**

- **FR-001**: The system MUST let an authenticated user list their own interests and MUST never return another user's interests.
- **FR-002**: Each listed interest MUST include the interest identifier, job identifier, interest creation time, and the job's header information (`id`, `title`, `company`, `location`, source URL, `source`, `postingDate`), where available.
- **FR-003**: Job header information MUST be read from the shared normalized job at request time and MUST NOT be stored in or duplicated by the interest record.
- **FR-004**: The listing MUST sort by interest creation time descending, using the interest identifier as a deterministic secondary order so pagination is stable when times are equal.
- **FR-005**: The listing MUST support optional `company`, `title`, and `location` filters on the normalized job, applied together with AND semantics, using case-insensitive partial matching; blank filters are ignored.
- **FR-006**: The listing MUST be paginated with a default page of 1 and default page size of 20, MUST reject a page size above the service-wide maximum (100) and any page or page size below 1 with the standard validation error, and MUST return the current page, page size, total matching records, and total pages.
- **FR-007**: Filtering, ownership restriction, sorting, counting, and pagination MUST be performed by the database, not by loading all records into application memory, and MUST be applied in that order: ownership and filters, then sort, then page.
- **FR-008**: A page beyond the last page, or a query with no matches, MUST return a successful empty result with accurate metadata.

**Add and remove**

- **FR-009**: The system MUST let an authenticated user add an existing normalized job to their own interests, retaining the current add operation's route and response shape.
- **FR-010**: The system MUST verify that the referenced job exists (not found otherwise) and has completed normalization (conflict otherwise). Any authenticated user is authorized to reference any such job because the catalog is shared.
- **FR-011**: The system MUST prevent more than one interest per user and job, both in application logic (adding again returns the existing interest) and through a database uniqueness constraint; a race that violates the constraint MUST resolve to the existing interest, not an error.
- **FR-012**: The system MUST let an authenticated user remove their own interest in a job. Removal MUST NOT delete or alter the normalized job.
- **FR-013**: Removing an interest that does not exist for the caller (including one owned only by someone else) MUST fail with the standard not-found error and MUST NOT affect other users' interests.
- **FR-014**: Interest ownership MUST be derived from the authenticated identity only; clients MUST NOT be able to name another user as the owner.

**Automatic creation**

- **FR-015**: When normalization and persistence of a submitted job succeed, the system MUST create an interest for the submitting user, committed atomically with the job's transition to its completed state.
- **FR-016**: When the submitted job already exists and is normalized, the system MUST reuse it under the existing deduplication rule (one job per source URL) and create the submitter's interest if absent.
- **FR-017**: Repeated or concurrent submissions MUST NOT create duplicate interests.
- **FR-018**: If creating the required interest fails, the system MUST treat it as a normalization workflow failure using the existing failure handling (failed job and processing record, logged, user-safe error) and MUST NOT report the operation as successful.
- **FR-019**: If normalization fails, no interest MUST be created.

**Application Journal integration**

- **FR-020**: The system MUST provide a reusable capability to release a user's interest in a job that participates in the caller's atomic unit of work, so that the Application Journal can create an entry and remove the interest in one transaction.
- **FR-021**: Releasing a non-existent interest MUST be a no-op, not an error. Releasing an interest MUST NOT delete the normalized job.
- **FR-022**: Interest Management MUST own interest records only. It MUST NOT implement application creation, status, recruiter information, contact dates, or status history, and MUST NOT introduce a combined "my jobs" listing.

**Security and conventions**

- **FR-023**: Every interest operation MUST require authentication and use the existing authentication, authorization, validation, and error-response conventions (standard error envelope with request identifier).
- **FR-024**: Deleting a normalized job MUST also remove interests referencing it.
- **FR-025**: The feature MUST reuse the existing user and normalized job entities and the existing interest record, and MUST NOT introduce new technologies or architectural components.
- **FR-026**: Logs and error responses MUST NOT expose secrets or other users' identifiers or interest data.

### Key Entities *(include if feature involves data)*

- **Interest**: A user's marker on a shared normalized job. Attributes: identifier, owning user, referenced job, creation time. Unique per user and job. Contains no job details, application status, or journal data. Owned by Interest Management.
- **Normalized Job**: The shared, URL-deduplicated job posting. Source of all header information shown with an interest. Never deleted by interest operations.
- **User**: The authenticated owner of interests. Each user has zero or more interests.
- **Interest Page**: A page of interest items (interest identifier, job identifier, creation time, job header) plus current page, page size, total matching records, and total pages.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance tests with two or more users, 100% of listed interests belong to the requester and 0 interests of other users are ever returned, modified, or removed.
- **SC-002**: 100% of listed interests show the job's header information, and changing a job's title or company is reflected in the listing without touching any interest.
- **SC-003**: After any number (including concurrent) of add requests and resubmissions for one user and job, exactly one interest exists.
- **SC-004**: 100% of jobs successfully normalized from a user's submission appear in that user's interests, and 0% of failed normalizations do.
- **SC-005**: Across successive pages of a known data set, every matching interest appears exactly once, newest first, including sets with equal creation times.
- **SC-006**: When creating an interest during normalization fails, the workflow is reported as failed in 100% of cases and no job is left reported as successfully completed without the interest.
- **SC-007**: Releasing an interest and recording an application either both take effect or neither does in 100% of tested failure scenarios.
- **SC-008**: At least 95% of listing requests for a user with up to 10,000 interests return within 2 seconds under normal load.
- **SC-009**: Removing an interest leaves the shared job retrievable in 100% of tests.

## Automated Test Scenarios

Tests follow the existing layers: contract (HTTP boundary), integration (database and normalization workflow), and unit.

**Contract**
- List: requires authentication; returns only own interests; item shape; default sort and page size; custom page and page size; page beyond last; each filter alone and combined; case-insensitive partial and wildcard-literal matching; invalid page/limit rejected; maximum page size enforced; empty result metadata.
- Add: success; duplicate returns existing; unknown job not found; non-normalized job conflict; unauthenticated rejected.
- Remove: success leaves job intact; no interest not found; another user's interest not found and untouched; unauthenticated rejected.
- Cross-user isolation across list, add, and remove.

**Integration**
- Normalization of a new job creates exactly one interest for the submitter, committed with job completion.
- Resubmitting the same URL (same user) leaves one interest; a second user gets their own interest on the same job.
- Forced interest-creation failure marks the workflow failed and the job not completed, with no interest.
- Normalization failure creates no interest.
- Unique constraint rejects a duplicate at the database layer; concurrent add resolves to one interest.
- Stable pagination with identical creation times; filtering, counting, and paging are executed in the database (verified by query count/shape with a data set larger than one page).
- Releasing an interest inside a unit of work with a simulated journal write: commit removes both effects together; failure of either rolls back both; absent interest is a no-op; job survives.
- Deleting a normalized job removes its interests.
- Migration applies and reverses cleanly and supports the listing query.

## Assumptions

- All authenticated users share one job catalog, so "authorized to reference a job" means the job exists and is normalized; per-job visibility rules do not exist.
- The existing add operation's route, `201` status, and response shape are preserved for backward compatibility; the new rejection of non-normalized jobs is the only behavior change and is considered a correction aligned with "existing normalized job".
- The Application Journal is a future, separate feature; this feature only guarantees the interest-release capability and its atomic behavior, which will be exercised in tests via a test double until the journal exists.
- Automatic interest creation for a newly submitted job occurs at normalization completion, because that is when "normalization and persistence succeed". For an existing job that is already normalized, it occurs at submission. For an existing job still in progress or failed, no interest is created by that request; the user can add it manually once it is normalized.
- Removing a missing interest is reported as not found (not silently successful) for the user-facing remove operation, and is a no-op only for the internal journal release.
- The existing shared-catalog filter behavior (case-insensitive partial match, blank ignored) and pagination bounds (default 20, maximum 100) from the normalized jobs listing are reused.
- Interest records are not versioned or soft-deleted; history of removed interests is out of scope.
- Supporting artifacts for planning: [contracts/api-v1.md](./contracts/api-v1.md) and [data-model.md](./data-model.md).
