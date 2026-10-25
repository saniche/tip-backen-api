# API V1 Contract: Application Journal

All endpoints require a bearer token. The authenticated principal supplies the owner ID; clients
cannot supply `userId`. Errors use the existing envelope:
`{"error":{"code","message","details","request_id"}}`. A record owned by another user is treated as
not found.

## Endpoints

| Method | Path | Success | Purpose |
|---|---|---|---|
| POST | `/api/v1/applications` | 201 | Create a journal entry for an existing normalized job |
| GET | `/api/v1/applications` | 200 | List caller's entries with filters and pagination |
| GET | `/api/v1/applications/{application_id}` | 200 | Retrieve one caller-owned entry |
| PATCH | `/api/v1/applications/{application_id}` | 200 | Partially update editable journal fields |
| PATCH | `/api/v1/applications/{application_id}/status` | 200 | Change current status and append history |
| DELETE | `/api/v1/applications/{application_id}` | 204 | Delete caller-owned entry and its history |

## Create

### Request

```json
{
  "jobId": "job-id",
  "recruiterInfo": {
    "name": "Alex Recruiter",
    "email": "alex@example.com",
    "phone": "+1-555-0100"
  },
  "contactDate": "2026-10-22",
  "followUpDate": "2026-10-29",
  "workAuthorizationDiscussed": false,
  "notes": "Applied through the company careers page"
}
```

`recruiterInfo`, `contactDate`, `followUpDate`, and `notes` may be omitted or null;
`workAuthorizationDiscussed` defaults to false. `status`, `history`, `userId`, and job-header
fields are not accepted as create inputs. The entry always starts at `NotStarted` with one
corresponding history item with null note.

### Response `201`

Returns the complete `ApplicationJournalItem` shape defined below. The create operation validates
that the job exists and is normalized, inserts the journal and initial history, and removes a
matching caller interest if present in one transaction. Missing interest is a no-op.

## List

### Query parameters

| Name | Type | Default | Constraints / behavior |
|---|---|---|---|
| `company` | string | — | Case-insensitive partial match against `job.company` |
| `title` | string | — | Case-insensitive partial match against `job.title` |
| `location` | string | — | Case-insensitive partial match against `job.location` |
| `page` | integer | `1` | One-based; minimum 1 |
| `limit` | integer | `20` | Minimum 1; maximum 100 |

Blank filters are ignored, and supplied filters combine with AND semantics. `%` and `_` are
treated as literal characters, following the existing interest listing. Ownership, filtering,
count, ordering, and pagination are database-side.

### Ordering

`application_journals.created_at DESC, application_journals.id DESC`.

### Response `200`

```json
{
  "items": [
    {
      "id": "application-id",
      "jobId": "job-id",
      "recruiterInfo": {
        "name": "Alex Recruiter",
        "email": "alex@example.com",
        "phone": "+1-555-0100"
      },
      "contactDate": "2026-10-22",
      "followUpDate": "2026-10-29",
      "workAuthorizationDiscussed": false,
      "notes": "Applied through the company careers page",
      "status": "NotStarted",
      "history": [
        {
          "date": "2026-10-23T12:00:00Z",
          "note": null,
          "status": "NotStarted"
        }
      ],
      "createdAt": "2026-10-23T12:00:00Z",
      "updatedAt": "2026-10-23T12:00:00Z",
      "job": {
        "id": "job-id",
        "title": "Software Engineer",
        "company": "Example Co",
        "location": "Remote",
        "url": "https://example.com/jobs/1",
        "source": "CompanyWebsite",
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

Optional job header values may be null. `recruiterInfo`, contact/follow-up dates, and notes may be
null. History is ordered by `date ASC`, then history identifier ascending for equal timestamps.
`totalPages` is `ceil(total / limit)` and zero when no matches exist. A page past the last page
returns `200` with an empty `items` list and unchanged matching totals.

## Retrieve

`GET /api/v1/applications/{application_id}` returns one complete journal item. Missing and
foreign-owner IDs return `404 RESOURCE_NOT_FOUND`.

## Update editable fields

### Request

`PATCH /api/v1/applications/{application_id}` accepts any non-empty subset of:

```json
{
  "recruiterInfo": {"name": "Alex Recruiter", "email": null, "phone": "+1-555-0100"},
  "contactDate": "2026-10-22",
  "followUpDate": null,
  "workAuthorizationDiscussed": true,
  "notes": "Sent a follow-up email"
}
```

Null values explicitly clear nullable fields. Fields omitted from the request remain unchanged.
`status`, `history`, `jobId`, `userId`, and job-header fields are forbidden. Response is the
complete updated journal item. No status history item is added.

## Update status

### Request

`PATCH /api/v1/applications/{application_id}/status`

```json
{
  "status": "Interview",
  "note": "Technical interview scheduled"
}
```

`status` is required and must be exactly one of the supported values. `note` is optional and
nullable. If the status differs from the current status, the service updates current status and
appends one timestamped history record atomically. If unchanged, the operation returns the
unchanged record and adds no history item.

## Delete

`DELETE /api/v1/applications/{application_id}` returns `204 No Content` for a deleted owned entry.
The normalized job remains unchanged; no interest is recreated. Missing or foreign-owner IDs
return `404 RESOURCE_NOT_FOUND`.

## Errors

| Condition | Status | Code / behavior |
|---|---|---|
| Missing/invalid bearer token | 401 | `UNAUTHORIZED` |
| Invalid body, date, recruiter fields, pagination values, or status | 422 | Existing validation response |
| Journal ID missing or owned by another user | 404 | `RESOURCE_NOT_FOUND` |
| Job ID missing | 404 | `RESOURCE_NOT_FOUND` |
| Job exists but normalization is not completed | 409 | `CONFLICT` |
| Duplicate owner/job journal entry | 409 | `CONFLICT` |

No administrative exception grants access to other users' journal records.
