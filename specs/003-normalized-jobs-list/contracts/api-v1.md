# API V1 Contract: Normalized Jobs Listing

## Operation

| Method | Path | Authentication | Purpose |
|---|---|---|---|
| GET | `/api/v1/jobs/normalized` | Required bearer token | List successfully normalized jobs using a compact header-only shape |

This is a new operation. The behavior and response shape of `GET /api/v1/jobs` remain unchanged.

## Query Parameters

| Name | Type | Required | Default | Constraints / behavior |
|---|---|---|---|---|
| `title` | string | No | — | Case-insensitive substring filter |
| `company` | string | No | — | Case-insensitive substring filter |
| `location` | string | No | — | Case-insensitive substring filter |
| `page` | integer | No | `1` | One-based; minimum `1` |
| `limit` | integer | No | `20` | Minimum `1`, maximum `100` |

All supplied filters are combined with AND semantics. Empty or whitespace-only filters are ignored. Results include all eligible jobs in the shared catalog, not only jobs submitted by the authenticated user.

## Ordering and Eligibility

- Only jobs with completed normalization are returned.
- Results are ordered by `postingDate` descending. Missing or unparseable dates appear after valid dates.
- ISO 8601 date and datetime strings are treated as valid dates; returned `postingDate` values are not rewritten.
- Equal or unavailable dates are ordered by `id` ascending to stabilize page ordering.
- Filtering and total-count calculation occur before pagination.

## Successful Response

**Status**: `200 OK`

```json
{
  "items": [
    {
      "id": "job-id",
      "title": "Senior Engineer",
      "company": "Example Co",
      "location": "Remote",
      "postingDate": "2026-10-01",
      "source": "Example Board"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20
}
```

Each item contains exactly `id`, `title`, `company`, `location`, `postingDate`, and `source`. `company`, `location`, `postingDate`, and `source` may be `null`. The pagination envelope is separate from the six-field item shape. No matches or a page beyond the last page returns `200 OK`, an empty `items` array, and the matching `total`.

## Errors

| Condition | Status | Behavior |
|---|---|---|
| Missing or invalid bearer token | `401 Unauthorized` | Existing authentication error behavior |
| Invalid `page` or `limit` | `422 Unprocessable Entity` | Existing request validation behavior |

No new error envelope or authentication mechanism is introduced.
