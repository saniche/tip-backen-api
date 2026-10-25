# Application Journal Quickstart

This guide validates the observable API contract in
[contracts/api-v1.md](./contracts/api-v1.md). It describes test scenarios, not implementation code.

## Prerequisites

- Python project dependencies installed.
- Local test configuration provides a test JWT secret and SQLite database as in
  `tests/conftest.py`.
- The application is available through the existing FastAPI test client or local server.
- A bearer token for an authenticated user and at least one normalized job (`status == completed`).

## Automated validation

Run the focused API, service, workflow, and migration tests:

```powershell
python -m pytest tests/contract/test_application_contract.py tests/unit/test_application_service.py tests/integration/test_application_workflow.py tests/integration/test_migrations.py
```

Expected outcomes:

- Create without an interest succeeds with `NotStarted` and one matching initial history record.
- Create with a matching interest removes both records atomically.
- Duplicate owner/job creation returns conflict; another user can create their own entry for the
  same shared job.
- List filtering, newest-first stable ordering, pagination metadata, normalized-job projection,
  and owner isolation match the contract.
- Editable-field updates preserve status history; status changes append exactly one event;
  repeated status updates append none.
- Foreign-owner retrieval/update/delete is reported as not found.
- Deleting an entry preserves the normalized job and does not recreate an interest.
- Migration upgrade and downgrade both succeed and keep existing job/interest data intact.

## Manual API flow

1. Authenticate using the existing auth endpoints and keep the bearer token.
2. Create a normalized job or choose an existing completed job.
3. `POST /api/v1/applications` with `jobId` and optional recruiter/date/note fields.
4. `GET /api/v1/applications` and verify the job header, initial status/history, ordering, and
   pagination metadata.
5. `PATCH /api/v1/applications/{application_id}` to update an editable field and confirm history
   is unchanged.
6. `PATCH /api/v1/applications/{application_id}/status` with `{"status":"Applied","note":"..."}`;
   confirm current status and a new chronological history record.
7. Repeat the same status and confirm no duplicate history record is created.
8. Optionally delete the entry and verify the normalized job remains.

## Contract references

- Request, response, filtering, ordering, pagination, and errors:
  [contracts/api-v1.md](./contracts/api-v1.md)
- Entity constraints, relationships, indexes, and transaction boundaries:
  [data-model.md](./data-model.md)
