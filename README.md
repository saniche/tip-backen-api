# Talent Intelligent Platform

Talent Intelligent Platform Backend API

## Local setup

Create a virtual environment, install dependencies, copy `.env.example` to `.env`, and set the
values there. The application loads `.env` automatically before importing authentication or database code:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --reload
```

The API is rooted at `/api/v1`. Profile uploads accept PDF, DOCX, and TXT files up to 10 MB.
Use Azure Blob Storage in deployed environments; tests and local development use the in-memory
fallback when `AZURE_STORAGE_CONNECTION_STRING=UseDevelopmentStorage=true`.

### Database configuration

PostgreSQL must be running and the database named in `DATABASE_URL` must already exist. The
application creates tables for development convenience, but it does not create the PostgreSQL
database itself. Create it before starting the server:

```powershell
psql -h localhost -U postgres -c "CREATE DATABASE \"jobprocess-db\";"
alembic upgrade head
uvicorn main:app --reload
```

For local development without PostgreSQL, use SQLite instead:

```dotenv
DATABASE_URL=sqlite+pysqlite:///./jobprocess.db
```

SQLite creates the database file automatically. For PostgreSQL, use a URL such as:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/jobprocess-db
```

Special characters in PostgreSQL usernames or passwords must be URL-encoded. For example, `@`
becomes `%40`.

### Environment variables

Copy `.env.example` to `.env`. The application loads `.env` automatically:

```powershell
Copy-Item .env.example .env
```

Required values include `DATABASE_URL` and `JWT_SECRET_KEY`. Azure Blob Storage uses
`AZURE_STORAGE_CONNECTION_STRING` and `CV_BLOB_CONTAINER`. When using a real Azure account,
temporary download URLs also use `AZURE_STORAGE_ACCOUNT_NAME` and `AZURE_STORAGE_ACCOUNT_KEY`.
Never commit `.env` or expose these credentials; rotate any credential that has been shared.

### OpenAI structured processing

Profile extraction, job normalization, matching, and CV tailoring require `OPENAI_API_KEY`. Each
operation may select a separate Structured Outputs-capable model; the default is `gpt-4o-mini`:

```dotenv
OPENAI_API_KEY=...
OPENAI_PROFILE_BUILDER_MODEL=gpt-4o-mini
OPENAI_JOB_NORMALIZER_MODEL=gpt-4o-mini
OPENAI_JOB_MATCHING_MODEL=gpt-4o-mini
OPENAI_CV_TAILORING_MODEL=gpt-4o-mini
OPENAI_TIMEOUT_SECONDS=60
```

Standard automated tests mock OpenAI calls and do not require an API key. Provider failures result
in a safe service error for matching or a failed processing job for profile, job, and CV workflows.

## Validation

```powershell
python -m pytest -q
python -m pytest -q tests/unit tests/contract tests/integration
alembic upgrade head
docker build -t job-process-api .
```
