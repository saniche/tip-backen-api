# Quickstart: Normalized Jobs Listing

## Prerequisites

- Python 3.11
- Project dependencies installed from `requirements.txt` and `requirements-dev.txt`
- No external AI credentials are required for these contract tests; the test fixtures stub structured processing.

## Run Focused Contract Tests

From the repository root:

```powershell
python -m pytest tests/contract/test_normalized_jobs_contract.py tests/contract/test_job_contract.py
```

Expected result: the normalized listing contract tests pass, and the existing jobs listing tests continue to pass unchanged.

## Validate Lint

```powershell
python -m ruff check jobs/job_normalizer.py shared/schemas.py tests/contract/test_normalized_jobs_contract.py
```

Expected result: no Ruff violations.

## Acceptance Scenarios

1. Authenticate using the existing test registration flow. Create completed jobs with varied titles, companies, locations, sources, and posting dates.
2. Request `/api/v1/jobs/normalized` without query parameters. Verify the response has `page: 1`, `limit: 20`, the correct pre-pagination `total`, newest posting date first, and exactly the six documented item fields.
3. Request `title`, `company`, and `location` filters individually and in combination. Verify every returned record matches every supplied filter; a no-match request returns an empty `items` array and `total: 0`.
4. Request subsequent pages with a smaller `limit`. Verify no eligible job is omitted or repeated and that the total remains consistent.
5. Include a job without a posting date and one with an unparseable date. Verify both sort after valid dates; verify equal-date rows use the stable tie-breaker.
6. Include pending and failed jobs. Verify neither appears in the listing.
7. Request invalid pagination values and an unauthenticated listing. Verify the service returns its standard `422` and `401` responses, respectively.
8. Run the existing `GET /api/v1/jobs` contract scenarios to verify that its response remains unchanged.

## Performance Acceptance

With a representative shared catalog and normal service load, measure listing response time and verify that at least 95% of requests complete within 2 seconds. Record the tested catalog size and request mix with the implementation's validation results.

### Local Synthetic Baseline (2026-10-13)

- Catalog: 10,000 completed jobs in the in-memory SQLite test database.
- Requests: 100 sequential authenticated `TestClient` requests; 80% unfiltered and 20% filtered by company.
- Environment: Python 3.13.2 on Windows.
- Results: p50 116.10 ms, p95 473.95 ms, maximum 699.46 ms. The local p95 met the 2-second target.
- Limitation: This sequential in-process baseline is not a production or concurrent-load measurement.

### Local Synthetic Concurrent Verification (2026-10-13)

- Catalog: 10,000 completed jobs in a temporary SQLite database.
- Requests: 100 authenticated `TestClient` requests with 10 concurrent workers; 80% unfiltered and 20% filtered by company.
- Environment: Python 3.13.2 on Windows.
- Results after database-side date ordering and pagination: p50 170.95 ms, p95 263.66 ms, maximum 302.58 ms. The local concurrent p95 met the 2-second target.
- Limitation: This is a synthetic in-process SQLite measurement, not a deployed PostgreSQL or production traffic test. Validate against representative deployed service load before treating the target as verified for production.
