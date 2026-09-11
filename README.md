# Talent Intelligent Platform

Talent Intelligent Platform Backend API

## Local setup

Create a virtual environment, install dependencies, and configure the values in `.env.example`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

The API is rooted at `/api/v1`. Profile uploads accept PDF, DOCX, and TXT files up to 10 MB.
Use Azure Blob Storage in deployed environments; tests and local development use the in-memory
fallback when `AZURE_STORAGE_CONNECTION_STRING=UseDevelopmentStorage=true`.

## Validation

```powershell
python -m pytest -q
python -m pytest -q tests/unit tests/contract tests/integration
alembic upgrade head
docker build -t job-process-api .
```
