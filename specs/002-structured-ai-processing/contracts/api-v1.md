# API V1 Contract: Structured AI Processing

## Compatibility

This feature adds no endpoint and removes none. Existing request and successful response shapes
remain unchanged; only the internal source of derived profile, job, matching, and CV data changes.

## Affected Operations

| Method | Path | Completion behavior | Successful result |
|--------|------|---------------------|-------------------|
| POST | `/api/v1/profile/sessions/{session_id}/files` | Asynchronous | Existing `202` file and processing-job identifiers |
| POST | `/api/v1/jobs/normalize` | Asynchronous | Existing `202` job and processing-job identifiers |
| POST | `/api/v1/matching` | Waits for validated structured assessments | Existing `202` report identifier and status |
| POST | `/api/v1/matching/match` | Waits for one validated structured assessment | Existing `200` matching-result shape |
| POST | `/api/v1/cv/tailor` | Asynchronous | Existing `202` processing-job shape |
| POST | `/api/v1/cv-tailoring/tailor` | Asynchronous | Existing `202` processing-job shape |

## Failure Behavior

| Condition | Synchronous matching | Asynchronous profile/job/CV |
|-----------|----------------------|-----------------------------|
| Provider unavailable, timeout, refusal, incomplete response, or invalid structured data | Existing safe service-unavailable error; no report/results persist | Request remains accepted after initial validation; processing resource reaches `failed` with a safe generic error |
| Missing provider configuration | Existing safe service-unavailable error | Processing resource reaches `failed` with a safe generic error |
| Invalid request or missing owned resource | Existing `400`, `404`, or `422` behavior | Existing `400`, `404`, or `422` behavior |

The existing error envelope is retained:

```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "External processing failed. Please try again later.",
    "details": null,
    "request_id": "..."
  }
}
```

Raw provider messages, keys, prompts, and submitted candidate data are never returned.

## Observable Data Guarantees

- Data exposed by existing GET endpoints is validated against its operation-specific structure.
- A failed later profile or CV attempt does not replace earlier completed data.
- A failed matching request creates no visible report or result.