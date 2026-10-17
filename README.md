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

The API is rooted at `/api/v1`. Profile uploads accept PDF, DOCX, TXT, and Markdown files up to 10 MB.
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

### OpenAI Responses API structured processing

Profile extraction, job normalization, matching, and CV tailoring use the OpenAI Python SDK's
Responses API and require `OPENAI_API_KEY`. OpenAI is the default structured LLM provider; each
operation may select a separate Structured Outputs-capable model, with `gpt-6-luna` as the default.
Reasoning effort is controlled by `OPENAI_REASONING_EFFORT` and defaults to `medium`:

```dotenv
OPENAI_API_KEY=...
OPENAI_PROFILE_BUILDER_MODEL=gpt-6-luna
OPENAI_JOB_NORMALIZER_MODEL=gpt-6-luna
OPENAI_JOB_MATCHING_MODEL=gpt-6-luna
OPENAI_CV_TAILORING_MODEL=gpt-6-luna
OPENAI_REASONING_EFFORT=medium
OPENAI_TIMEOUT_SECONDS=60
```

Standard automated tests mock OpenAI calls and do not require an API key. Provider failures result
in a safe service error for matching or a failed processing job for profile, job, and CV workflows.

### Job normalization

`POST /api/v1/jobs/normalize` requires the posting URL and raw content. Optional client-provided
`title`, `company`, and `location` values are retained instead of being replaced by the LLM:

```http
POST /api/v1/jobs/normalize
Content-Type: application/json

{
  "url": "https://www.indeed.com/viewjob?jk=example",
  "content": "Software Engineer ...",
  "company": "Example Inc."
}
```

The asynchronous normalizer extracts title, company, location, salary, source, posting date, key
responsibilities, mandatory `requirements`, preferred `desirables`, technical stack, and
`additionals`. Missing text metadata is an empty string and missing list values are empty lists.
If the LLM cannot determine a posting date, the system stores the day before the UTC processing
date as a fallback. Source is normalized to `LinkedIn`, `Indeed`, `JobBank`,
`CompanyWebsite`, or `Other`; relative posting dates are resolved from the processing date only
when the posting states a clear relative date. The completed normalized fields are available from
`GET /api/v1/jobs/{job_id}`.

Profile sessions accept an optional `output_language` when created. It defaults to English and is
applied to every file in that session, even if the source resumes use another language:

```http
POST /api/v1/profile/sessions
Content-Type: application/json

{"output_language": "French"}
```

Skill levels are `Expert`, `Advanced`, `Intermediate`, or `Beginner`, ordered from highest to
lowest. They are based only on experience duration and contributions supported by the resume;
skills without enough evidence for a level are omitted.

## Validation

```powershell
python -m pytest -q
python -m pytest -q tests/unit tests/contract tests/integration
alembic upgrade head
docker build -t job-process-api .
```
