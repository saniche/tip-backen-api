# Postman Integration Tests

Import `Talent-Intelligence-Platform.postman_collection.json` and
`Talent-Intelligence-Platform.local.postman_environment.json`, then run the collection in order
against a running local API. The collection generates a unique user email and propagates its token
and resource identifiers automatically.

The `profile_fixture_path` environment variable must resolve to
`postman/fixtures/profile.txt` from the Postman or Newman working directory. Set it to an absolute
path when your client cannot resolve relative upload paths.

Run it from the repository root with Newman:

```powershell
newman run postman/Talent-Intelligence-Platform.postman_collection.json -e postman/Talent-Intelligence-Platform.local.postman_environment.json
```

for jobcontent variation use this

```powershell
 .\postman\multi-job-process.ps1
```

for single jobcontent variation use this

```powershell
 .\postman\single-job-process.ps1
```

and follow with

```powershell
newman run postman/Talent-Intelligence-Platform.postman_collection.json -e postman/Talent-Intelligence-Platform.local.postman_environment.json -d postings.json
```

some usefules variation
**Force a single URL source for the whole run**

```powershell
newman run collection.json -d postings.json --env-var "jobSource=indeed"
```

**Run only the first 5 postings**

```powershell
newman run collection.json -d postings.json -n 5
```

**Export results for CI**

```powershell
newman run collection.json -d postings.json -r cli,junit --reporter-junit-export results.xml
```

The collection includes successful and expected-failure checks for all requested operational,
authentication, profile, processing job, matching, and CV tailoring routes. The job-normalization
folder is a prerequisite that supplies a real job for successful matching tests. Matching requests
return `202 Accepted`; the collection polls the matching processing job before requesting report
results.

## Interests folder

The `Interests` folder runs after job normalization completes and covers interest management for the
setup job (see `specs/004-interest-management/contracts/api-v1.md`):

- Normalization automatically creates the submitter's interest, which `GET /jobs/interests` returns
  with the job header (`id`, `title`, `company`, `location`, `url`, `source`, `postingDate`).
- Listing filters (case-insensitive partial `title`, `company`, `location`), page size, a page beyond
  the last, the no-match empty page, and `422` for `limit=101` and `page=0`.
- Add (`201` with `created` or `existing`), duplicate add, unknown job (`404`), and removal (`204`,
  the job still exists, then `404` when already removed).
- Resubmitting the same job URL recreates a removed interest and never duplicates it.
- A second registered user sees none of the first user's interests, cannot remove them (`404`), and
  gets a separate interest on the same job.
- Unauthenticated list, add, and remove return `401`.

The `Cleanup` folder also removes the setup job's interest. A `409` for adding a job whose
normalization has not completed is covered by the automated pytest suite, not Postman, because the
collection cannot create a job in that state.

## Application Journal folder

The `Application Journal` folder runs after `Interests` and covers job application tracking for the setup
job (see `specs/005-application-journal/contracts/api-v1.md`):

- **Creation & Atomic Interest Release**: `POST /applications` creates a journal entry for the normalized
  job initialized to `NotStarted` with initial history and automatically releases any matching interest.
  A follow-up check on `GET /jobs/interests` verifies the interest is no longer present.
- **Validation & Conflict Handling**: Duplicate creation returns `409 Conflict`; unknown job returns `404`;
  unauthenticated requests return `401`.
- **Listing, Filtering, & Pagination**: `GET /applications` tests default ordering (newest first),
  pagination metadata (`items`, `total`, `page`, `limit`, `totalPages`), case-insensitive partial filters
  (`title`, `company`, `location`), empty results on non-matching query, custom page size, page beyond last,
  and `422` validation for `limit > 100` and `page < 1`.
- **Retrieval & Partial Updates**: `GET /applications/{id}` retrieves the owned entry with full job header
  projection and history; `PATCH /applications/{id}` updates editable fields (`recruiterInfo`, `followUpDate`,
  `workAuthorizationDiscussed`, `notes`) while preserving history; empty update body or attempt to pass
  protected fields (`status`) returns `422`.
- **Status Transitions & History**: `PATCH /applications/{id}/status` appends an immutable history item
  and updates current status; repeating the same status is an idempotent no-op (no duplicate history appended);
  unsupported status returns `422`.
- **User Isolation**: A second registered user sees zero entries in their list, receives `404` when
  attempting to view, update fields, update status, or delete the first user's entry, and can independently
  create and delete their own journal entry for the same shared job.
- **Cleanup**: In the `Cleanup` folder, `DELETE /applications/{id}` verifies removal with `204`, missing
  entry removal with `404`, and confirms the underlying normalized job remains retrievable.

