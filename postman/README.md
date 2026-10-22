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
