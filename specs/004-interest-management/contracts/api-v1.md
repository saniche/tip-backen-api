# API V1 Contract: Interest Management

All operations require a bearer token and use the existing error envelope
(`{"error": {"code", "message", "details", "request_id"}}`). Ownership always comes from the
authenticated user; no user identifier is accepted from the client.

| Method | Path | Status | Purpose |
|---|---|---|---|
| GET | `/api/v1/jobs/interests` | 200 | List the caller's interests (new) |
| POST | `/api/v1/jobs/{jobId}/interest` | 201 | Add an interest (existing; hardened) |
| DELETE | `/api/v1/jobs/{jobId}/interest` | 204 | Remove the caller's interest (new) |

`GET /jobs/interests` MUST be registered before `GET /jobs/{job_id}` so the literal segment is not
captured as a job identifier. Existing `GET /jobs`, `GET /jobs/normalized`, `GET /jobs/{id}`,
`POST /jobs/normalize`, and `DELETE /jobs/{id}` keep their shapes.

## GET `/api/v1/jobs/interests`

### Query parameters

| Name | Type | Default | Constraints / behavior |
|---|---|---|---|
| `company` | string | — | Case-insensitive substring on the job's company |
| `title` | string | — | Case-insensitive substring on the job's title |
| `location` | string | — | Case-insensitive substring on the job's location |
| `page` | integer | `1` | One-based; minimum `1` |
| `limit` | integer | `20` | Minimum `1`, maximum `100` |

Filters combine with AND; blank/whitespace-only filters are ignored; `%` and `_` match literally.
Processing order: restrict to caller → apply filters → count → sort → page, all in the database.

### Ordering

`interest.created_at DESC, interest.id DESC` (stable tie-break).

### Response `200 OK`

```json
{
  "items": [
    {
      "id": "interest-id",
      "jobId": "job-id",
      "createdAt": "2026-10-21T19:00:00Z",
      "job": {
        "id": "job-id",
        "title": "Senior Engineer",
        "company": "Example Co",
        "location": "Remote",
        "url": "https://example.com/jobs/1",
        "source": "Example Board",
        "postingDate": "2026-10-01"
      }
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20,
  "totalPages": 1
}
```

`company`, `location`, `url`, `source`, and `postingDate` may be `null`. `totalPages` is
`ceil(total / limit)` and `0` when `total` is `0`. A page beyond the last returns an empty `items`
array with the unchanged `total` and `totalPages`. The `job` object is a projection of the shared job
and is never stored with the interest.

### Errors

| Condition | Status | Code |
|---|---|---|
| Missing/invalid token | 401 | `UNAUTHORIZED` |
| Invalid `page` or `limit` | 422 | Existing request-validation response (FastAPI default body) |

## POST `/api/v1/jobs/{jobId}/interest`

No request body. Response (unchanged shape):

| Case | Status | Body |
|---|---|---|
| Interest created | 201 | `{"id": "<interestId>", "status": "created"}` |
| Interest already exists | 201 | `{"id": "<interestId>", "status": "existing"}` |

Concurrent duplicate creation resolves to the `existing` response.

### Errors

| Condition | Status | Code |
|---|---|---|
| Missing/invalid token | 401 | `UNAUTHORIZED` |
| Job does not exist | 404 | `RESOURCE_NOT_FOUND` |
| Job normalization not completed (new rule) | 409 | `CONFLICT` |

## DELETE `/api/v1/jobs/{jobId}/interest`

No body. Deletes only the caller's interest in that job; the job is untouched.

| Case | Status |
|---|---|
| Removed | 204, empty body |

### Errors

| Condition | Status | Code |
|---|---|---|
| Missing/invalid token | 401 | `UNAUTHORIZED` |
| Job missing, or caller has no interest in it (including only another user does) | 404 | `RESOURCE_NOT_FOUND` |

## Effect on `POST /api/v1/jobs/normalize`

Request and response shapes are unchanged (`202`, `{"id", "status", "processing_job_id", ...}`, or
`{"id", "status": "existing"}`).

- New job: the submitter's interest is created in the same transaction that marks the job
  `completed` and the processing job `done`. If the interest write fails, the transaction rolls back
  and the existing failure path runs (job `failed`, processing job `failed` with "Job normalization
  failed"); status polling reports the failure.
- Existing, completed job: the submitter's interest is created (idempotently) before responding with
  `{"status": "existing"}`; a failure surfaces as the standard error response, not as success.
- Existing job still `pending`/`processing`/`failed`: no interest is created by the request.

## Internal Capability (Application Journal)

Not an HTTP endpoint. A reusable operation, e.g. `release_interest(db, user_id, job_id)`:

- Deletes the `(user_id, job_id)` interest using the caller's session; it MUST NOT commit, so the
  Application Journal's insert and the interest delete share one transaction.
- Returns whether a row was removed; a missing interest is a no-op, not an error.
- Never touches the job row or other users' interests.
