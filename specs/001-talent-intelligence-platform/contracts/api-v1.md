# REST Contract: API V1

All capability routes are rooted at `/api/v1` and require an access token except registration and login. Long-running create operations return `202` with a processing resource.

## Common Behavior

| Condition | Status |
|---|---:|
| Read or completed operation | 200 |
| Resource created | 201 |
| Processing accepted | 202 |
| Invalid input | 400 or 422 |
| Missing or invalid credentials | 401 |
| Owner or role not authorized | 403 |
| Resource absent | 404 |
| Duplicate or invalid resource state | 409 |
| AI provider unavailable | 503 |

Errors use `{ "error": { "code", "message", "details", "request_id" } }`. Responses never contain credentials, stack traces, raw provider failures, or storage paths.

## Authentication

| Method | Path | Request | Result |
|---|---|---|---|
| POST | `/auth/register` | email and password | 201 access token |
| POST | `/auth/login` | credentials | 200 access token |

## Profile Processing

| Method | Path | Request | Result |
|---|---|---|---|
| POST | `/profile/sessions` | optional output language | 201 profile session |
| POST | `/profile/sessions/{sessionId}/files` | one valid document | 202 file and processing state |
| GET | `/profile/sessions/{sessionId}` | none | session and file statuses |
| GET | `/profile` | none | current canonical profile |
| PUT | `/profile` | editable profile fields | 200 updated profile version |

## Jobs and Interests

| Method | Path | Request | Result |
|---|---|---|---|
| POST | `/jobs/normalize` | source URL and raw posting content | 202 processing state |
| GET | `/jobs` | date, title, company, location, ordering, pagination | 200 newest-first job page |
| GET | `/jobs/{jobId}` | none | 200 job |
| POST | `/jobs/{jobId}/interest` | none | 201 interest |
| DELETE | `/jobs/{jobId}` | none | 204 for submitter or administrator |

## Matching and CVs

| Method | Path | Request | Result |
|---|---|---|---|
| POST | `/matching` | one or more job IDs | 202 match report state |
| GET | `/matching/reports` | pagination | 200 owner's reports |
| GET | `/matching/reports/{reportId}` | none | 200 ranked immutable results |
| DELETE | `/matching/reports/{reportId}` | none | 204 owner only |
| POST | `/cv/tailor` | match result IDs and `per_job` or `group_all` mode | 202 CV request state |
| GET | `/cv` | pagination | 200 owner's CVs |
| GET | `/cv/{cvId}` | none | 200 CV metadata or viewable content |
| GET | `/cv/{cvId}/download` | none | 200 authorized temporary URL |
| DELETE | `/cv/{cvId}` | none | 204 owner only |

## Operational Routes

| Method | Path | Result |
|---|---|---|
| GET | `/processing-jobs/{jobId}` | Owner-visible processing status and safe failure message |
| GET | `/health` | Process health |
| GET | `/ready` | Dependency readiness |