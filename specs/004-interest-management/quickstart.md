# Quickstart: Validating Interest Management

Prerequisites: Python 3.11 with `requirements.txt` and `requirements-dev.txt` installed in the project virtual environment. Tests use in-memory SQLite and a fake AI provider; no external services or secrets are needed.

## Automated validation

```powershell
.\.venv\Scripts\python.exe -m pytest tests\contract\test_interest_contract.py tests\integration\test_interest_workflow.py tests\unit\test_interest_service.py -q
.\.venv\Scripts\python.exe -m pytest tests\contract\test_job_contract.py tests\integration\test_job_normalization.py tests\integration\test_migrations.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

Expected: all tests pass. Ruff reports 37 pre-existing findings in unrelated files (none in the files this feature touches); run `ruff check jobs shared alembic tests\contract\test_interest_contract.py tests\integration\test_interest_workflow.py tests\unit\test_interest_service.py` for a clean result. The second command confirms existing job, normalization, and migration behavior is unchanged.

## Manual validation (running API)

Run the API with a local database, apply migrations (`alembic upgrade head`), register two users A and B, and use their bearer tokens. Routes, parameters, and response shapes are defined in [contracts/api-v1.md](./contracts/api-v1.md).

1. **Auto-interest**: As A, submit a job to `POST /api/v1/jobs/normalize`, poll the processing job until `done`, then `GET /api/v1/jobs/interests` → the job appears once with its header.
2. **Dedup**: As A, resubmit the same URL → `existing`; the interest list still has one entry. As B, submit the same URL → B gets one interest on the same job; A's list is unchanged.
3. **Isolation**: As B, `GET /api/v1/jobs/interests` shows only B's interest. As B, `DELETE /api/v1/jobs/{jobId}/interest` for a job B has no interest in → `404`; A's interest remains.
4. **Add/remove**: As A, `DELETE` the interest → `204`; `GET /api/v1/jobs/{jobId}` still returns the job. `POST /api/v1/jobs/{jobId}/interest` twice → `201` with `created` then `existing`. `POST` for an unknown id → `404`; for a failed/in-progress job → `409`.
5. **Listing**: Seed more than 20 interests; verify default page of 20, `totalPages`, `page=2`, `limit=101` → `422`, combined `company`/`title`/`location` filters, and a page beyond the last (empty `items`, same `total`).
6. **Failure path**: Force the interest write to fail during normalization (covered by the integration test) → the processing job reports `failed`, the job is not `completed`, and no interest exists.

## Journal readiness check

The integration test `test_release_interest_is_atomic_with_journal_write` simulates a journal insert plus `release_interest` in one transaction and verifies commit and rollback outcomes; it is the acceptance evidence for criterion 8 until the Application Journal exists.

## Migration check

`alembic upgrade head` then `alembic downgrade -1` on a throwaway SQLite database both succeed; `PRAGMA index_list('job_interests')` includes `ix_job_interests_user_created` after upgrade and not after downgrade. Verified (upgrade → downgrade → upgrade) and covered by `tests/integration/test_migrations.py`.

## Performance validation (SC-008)

Measured 2026-10-21 with the in-process `TestClient` against in-memory SQLite, one user with 10,000 interests across 10,000 jobs, 100 requests per scenario:

| Scenario | p50 | p95 | Max |
|---|---|---|---|
| Default page (page 1, limit 20) | 43.4 ms | 139.9 ms | 481.5 ms |
| Deep page (`page=250`) | 56.8 ms | 165.3 ms | 332.9 ms |
| Filtered (`company=company 5&location=toronto`, 200 matches) | 56.1 ms | 112.2 ms | 263.9 ms |

All are far below the 2-second target. Caveat: this is a single-process, single-client measurement on SQLite and includes authentication and serialization overhead; it is not a PostgreSQL measurement under production concurrency, so re-check with the deployed database if the target is ever at risk.
