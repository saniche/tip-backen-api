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
alembic upgrade head
uvicorn main:app --reload
```

Redis must be running at `REDIS_URL`. In a second terminal, using the same environment and database,
start the worker:

```powershell
python -m arq shared.worker.WorkerSettings
```

The API is rooted at `/api/v1`. Profile uploads accept PDF, DOCX, TXT, and Markdown files up to 10 MB.
Use Azure Blob Storage in deployed environments. When
`AZURE_STORAGE_CONNECTION_STRING=UseDevelopmentStorage=true`, local development stores documents
in the `.local-blobs` directory instead of connecting to an emulator. Set `LOCAL_BLOB_DIRECTORY`
to change the directory; all application processes must share the same location. This directory
contains user documents and should be protected and backed up appropriately.

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

### Background processing

Profile extraction, job normalization, matching, CV tailoring and document tailoring run in ARQ
workers, not in the API process. Redis is required for new submissions. The API returns `503` if
the queue cannot be reached; it does not fall back to in-process execution. Successful submissions
retain their existing `202` response and can be polled through `/api/v1/processing-jobs/{id}`.

The database outbox stores committed work, and the worker periodically reconciles it with Redis.
Publication and database commits cannot be atomic: a timeout can return `503` even when work was
accepted or is subsequently recovered. There is no client idempotency key, so retrying such a
submission can create another operation. Monitor outbox and worker errors and investigate pending
or running jobs that do not progress.

`ARQ_MAX_ATTEMPTS` is the maximum total execution attempts, including the first; it defaults to 3
and accepts 1–3. Whole-job transient failures may be retried; permanent failures are exposed on
the processing job. Combined document tailoring retains partial results rather than retrying
individual failed documents. Delivery is at least once: a worker crash can repeat an AI call and
incur additional cost. After an abrupt worker loss, Redis can retain ARQ's in-progress marker for
up to `ARQ_JOB_TIMEOUT_SECONDS` plus ten seconds before another worker can resume the job.

The API and every worker must use the same persistent database and document storage. In-memory
SQLite is not supported by the worker. If using file-based SQLite locally, use the same absolute
database path and the same absolute `WORKER_LOCK_DIRECTORY` for all worker processes. When API
and worker run in separate containers with local file storage, mount the same directory at the
same `LOCAL_BLOB_DIRECTORY` in each container. Production should use PostgreSQL and Azure Blob
Storage. All processes for one environment must use the same `ARQ_QUEUE_NAME`; use a separate
queue name for each database or environment. Use a protected Redis connection, including
`rediss://` when TLS is required, and restrict Redis access to trusted services.

### Production worker rollout

The deployment workflow uses the external Compose configuration in `/opt/tip`. Before deploying,
configure a `worker` service there using the same image, environment, database, Redis connection,
and storage configuration as the `api` service, with a restart policy such as `unless-stopped`
and this command:

```text
python -m arq shared.worker.WorkerSettings
```

The workflow pulls both services, applies Alembic migrations, starts the API and worker, and checks
the API and worker health. Redis is already provisioned separately and is not modified by the
workflow. Drain existing in-process work before the first rollout: jobs started by the old API
are not in the new outbox and cannot be recovered by the new worker.

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
OPENAI_COVER_LETTER_TAILORING_MODEL=gpt-6-luna
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

To include the separate-worker Redis integration tests, set `TEST_REDIS_URL` to an isolated Redis
database. Set `TEST_POSTGRES_URL` to a disposable PostgreSQL database to additionally exercise the
production locking path. The tests create and drop uniquely named PostgreSQL schemas.
