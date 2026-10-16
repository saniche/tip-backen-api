# Feature Specification: Normalized Jobs Listing

**Feature Branch**: `003-normalized-jobs-list`

**Created**: 2026-10-12

**Status**: Draft

**Input**: User description: "Add a new endpoint to list all jobs (normalized). Include these filters title, company, location and location. The result is paginated, default page size = 20. Default order postingDate desc."

## Clarifications

### Session 2026-10-12

- Q: Which fields should the normalized jobs listing return? → A: Only header information: id, title, company, location, postingDate, and source.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse Normalized Jobs (Priority: P1)

As a job seeker, I want to browse normalized job postings so that I can discover available opportunities using consistent job information.

**Why this priority**: Access to a complete and consistently structured listing is the core value of the feature.

**Independent Test**: Request the first page when more than 20 normalized jobs are available and verify that it contains up to 20 header-only job records in the required posting-date order.

**Acceptance Scenarios**:

1. **Given** normalized jobs are available, **When** a job seeker requests the listing without pagination options, **Then** the response contains the first page with no more than 20 jobs and identifies the total number of matching jobs.
2. **Given** jobs have different posting dates, **When** the first page is requested, **Then** jobs are ordered from newest posting date to oldest.
3. **Given** no normalized jobs are available, **When** a job seeker requests the listing, **Then** the response contains an empty page and a total of zero.

---

### User Story 2 - Find Jobs by Posting Details (Priority: P1)

As a job seeker, I want to filter the listing by title, company, and location so that I can focus on relevant opportunities.

**Why this priority**: These filters let job seekers narrow the shared listing to opportunities that meet their immediate needs.

**Independent Test**: Seed postings with varied titles, companies, and locations, then request the listing with each filter individually and in combination; verify every returned job matches all supplied filters.

**Acceptance Scenarios**:

1. **Given** normalized jobs with different titles, **When** a title filter is supplied, **Then** only jobs with a matching title are returned.
2. **Given** normalized jobs with different companies and locations, **When** a company or location filter is supplied, **Then** only jobs matching that filter are returned.
3. **Given** multiple filters are supplied, **When** the listing is requested, **Then** all supplied filters are applied together.
4. **Given** no normalized job matches the supplied filters, **When** the listing is requested, **Then** the response contains an empty page and a total of zero.

---

### User Story 3 - Navigate Listing Pages (Priority: P2)

As a job seeker, I want to request later pages and choose a page size so that I can move through the full set of matching opportunities.

**Why this priority**: Pagination keeps listing responses manageable while making all matching postings accessible.

**Independent Test**: Request successive pages from a known set of normalized postings and verify that the pages cover the matching set without duplicate or missing jobs.

**Acceptance Scenarios**:

1. **Given** more than one page of matching jobs exists, **When** a later page is requested, **Then** that page contains the corresponding jobs and reports the same total matching count.
2. **Given** a supported page size is requested, **When** the listing is returned, **Then** it contains no more than that number of jobs.
3. **Given** a page is requested beyond the last page, **When** the listing is returned, **Then** the response contains an empty page and the total matching count.

### Edge Cases

- A normalized job has no posting date or has a posting date that cannot be interpreted; it is returned after jobs with valid posting dates.
- Multiple jobs share a posting date; all remain eligible for pagination without omissions or duplication between pages.
- A filter has no matching jobs; pagination metadata remains valid and the result list is empty.
- A requested page number or page size is invalid; the request is rejected with the service's standard input-validation response rather than silently changing the requested value.
- Jobs still being normalized or whose normalization failed are not presented as normalized listings.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST offer a new listing of normalized job postings without changing the behavior of the existing jobs listing.
- **FR-002**: The listing MUST include only jobs whose normalization has completed successfully.
- **FR-003**: Each listed job MUST contain only these header fields: `id`, `title`, `company`, `location`, `postingDate`, and `source`. It MUST NOT include other normalized job details.
- **FR-004**: The listing MUST support filtering by title, company, and location. When multiple filters are supplied, a job MUST satisfy every supplied filter to be included.
- **FR-005**: Text filters MUST match case-insensitively against the corresponding job field and MUST allow matching text within a field value.
- **FR-006**: The listing MUST be paginated, default to page 1 and a page size of 20, and report the total number of jobs matching the filters independently of the requested page.
- **FR-007**: The listing MUST allow callers to request a page size other than the default within the service's supported range.
- **FR-008**: The listing MUST order jobs by posting date descending by default. Jobs without a valid posting date MUST appear after jobs with valid dates.
- **FR-009**: The system MUST return a valid empty result and pagination metadata when no jobs match or the requested page contains no jobs.
- **FR-010**: The listing MUST enforce the service's existing authentication and error-handling conventions.

### Key Entities *(include if feature involves data)*

- **Normalized Job**: A successfully processed job posting. The listing exposes its identifier, title, company, location, posting date, and source as header information.
- **Paginated Listing**: A page of header-only job records matching the supplied filters, together with the requested page, effective page size, and total number of matching jobs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When at least 20 normalized jobs match and no page size is provided, the first page contains exactly 20 jobs; when fewer than 20 match, it contains every match.
- **SC-002**: In acceptance tests, 100% of returned jobs satisfy every supplied title, company, and location filter.
- **SC-003**: In acceptance tests, all matching jobs can be retrieved across successive pages with no omissions or duplicates, and each page is ordered by posting date descending.
- **SC-004**: At least 95% of listing requests under normal service load return a usable page or empty result within 2 seconds.
- **SC-005**: Job seekers can browse results with the default page size and identify each posting by its `id`, `title`, `company`, `location`, `postingDate`, and `source` without retrieving a separate job record.

## Assumptions

- “Location” appearing twice in the request is a duplicate; the distinct filters are title, company, and location.
- “Normalized jobs” means jobs whose normalization completed successfully; pending and failed jobs are excluded.
- Filter matching is case-insensitive substring matching, consistent with the existing job-listing behavior.
- Posting dates that are missing or invalid sort after valid dates. When dates are equal, the listing uses a consistent tie-break order so pagination remains stable.
- The endpoint follows the service's existing authentication, pagination bounds, and standard validation/error behavior. The exact maximum page size is governed by the existing service convention.
- “All jobs” refers to all successfully normalized job postings available to the authenticated caller, not only jobs submitted by that caller.
