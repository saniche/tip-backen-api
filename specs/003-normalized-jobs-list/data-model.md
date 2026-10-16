# Data Model: Normalized Jobs Listing

## Existing Entity: Job

The feature reads the existing globally shared and URL-deduplicated `Job` record. It does not add or alter persisted fields.

| Field | Existing storage | Listing behavior |
|---|---|---|
| `id` | Required string identifier | Returned as `id`; stable tie-break value |
| `title` | Required string | Returned and filterable by case-insensitive substring |
| `company` | Nullable string | Returned; filterable by case-insensitive substring |
| `location` | Nullable string | Returned; filterable by case-insensitive substring |
| `posting_date` | Nullable string | Returned as `postingDate`; sorted newest-first when parseable |
| `source` | Nullable string | Returned |
| `status` | String processing state | Only `completed` jobs are listed |

Other fields stored on a job, including URL, summary, salary, responsibilities, qualifications, preferences, and technical stack, are deliberately excluded from listing items.

### Listing Eligibility and Ordering

- A job is eligible only after normalization has completed successfully (`status = completed`).
- The catalog is global; authentication is required, but results are not filtered to the current user's submitted jobs.
- Valid posting-date values sort newest-first. Missing and unparseable dates sort after valid dates.
- Jobs with equal or unavailable posting dates use ascending `id` order as a stable tie-break.

## Response Entities

### Normalized Job Header

The list item is a read-only projection with exactly these fields:

| Field | Type | Nullable |
|---|---|---|
| `id` | string | No |
| `title` | string | No |
| `company` | string | Yes |
| `location` | string | Yes |
| `postingDate` | string | Yes |
| `source` | string | Yes |

The `postingDate` response name maps to the existing stored `posting_date` field; its stored value is returned without rewriting it. ISO 8601 date and datetime strings are sortable dates; missing or unparseable strings sort last.

### Normalized Jobs Page

| Field | Type | Meaning |
|---|---|---|
| `items` | array of Normalized Job Header | Current page of matching jobs |
| `total` | integer | Total eligible jobs matching the filters, before pagination |
| `page` | integer | One-based requested page |
| `limit` | integer | Effective page size |

## Query Inputs and Validation

- `title`, `company`, and `location` are optional text filters; all supplied filters must match.
- Text matching is case-insensitive substring matching.
- `page` defaults to 1 and must be at least 1.
- `limit` defaults to 20 and must be between 1 and 100 inclusive.
- Blank filters are treated as omitted.
- A page beyond the last page returns an empty `items` array with the unchanged matching `total`.
