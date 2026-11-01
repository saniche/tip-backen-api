# API documentation

The API is rooted at `/api/v1`. While the service is running, use:

- `/docs` for interactive Swagger UI. Select **Authorize** and paste the bearer access token
  returned by the JSON login endpoint.
- `/redoc` for the ReDoc reference.
- `/openapi.json` for the raw OpenAPI document.

Generate or refresh the checked-in OpenAPI document from the project root:

```powershell
.\.venv\Scripts\python.exe scripts\export_openapi.py
```

The exporter fails if a successful API operation has no response schema (204 responses have no
body). Run the contract test with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\contract\test_openapi.py
```

## Schema and entity separation

SQLAlchemy entities belong under `db/models/`. HTTP request, response, error, pagination, and shared
value-object contracts belong under `api/schemas/requests/`, `api/schemas/responses/`, and
`api/schemas/common/`. API schemas must not import SQLAlchemy, and database entities must not define
Pydantic request or response models. Routers map entity data into response schemas; never return
ORM entities directly. `shared/models.py` and `shared/schemas.py` are compatibility re-export
modules only.

File-upload operations use multipart form data. Tailored-document download operations return
`text/markdown` and include an attachment filename plus a short-lived, read-only download URL.
Storage account credentials are not included in API responses.
