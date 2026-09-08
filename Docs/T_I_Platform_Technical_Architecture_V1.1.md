# TALENT INTELLIGENCE PLATFORM
## TECHNICAL ARCHITECTURE SPECIFICATION

**Version:** 1.1  
**Status:** Current technical baseline  
**Scope:** Backend/API and supporting infrastructure  
**Date:** 2026-09-08

---

## 1. PURPOSE AND SCOPE

This document defines the technical architecture for the Talent Intelligence Platform, with the primary focus on the backend API and the services required to support the functional capabilities defined in the Functional Specification V1.1.

The platform provides four core capabilities:

1. Profile Processing
2. Job Normalization
3. Intelligent Matching
4. CV Tailoring

This specification distinguishes between:

- **Current / V1 requirements** — required for the initial implementation.
- **Coming Soon / Future** — planned evolution that is not required for the current implementation.

The architecture is intentionally backend-focused. Client applications are consumers of the API and are not part of the primary implementation scope of this document.

---

## 2. ARCHITECTURE PRINCIPLES

| Principle | Description |
|---|---|
| **API First** | All platform capabilities are exposed through a versioned REST API. |
| **Stateless API** | The API does not maintain user session state between requests. |
| **Async for Long-Running Operations** | LLM and document-processing operations execute through FastAPI BackgroundTasks in V1. |
| **Separation of Concerns** | API, application services, domain/business rules, and infrastructure concerns remain separated. |
| **Provider Independence** | Business services do not depend directly on a specific LLM provider or authentication implementation. |
| **Deterministic Business Rules** | Business-critical calculations such as matching scores, eligibility, weighting, and ranking are performed by the backend. |
| **Security by Design** | Authentication, authorization, resource ownership, input validation, secure storage, and secret management are part of the architecture. |
| **Cloud Ready** | The solution is designed for Azure deployment without requiring distributed infrastructure in V1. |
| **Observable Processing** | Long-running operations expose status and failures and generate structured logs. |
| **Testability** | Business logic and external dependencies are isolated so that unit, integration, and API tests can be implemented independently. |

---

## 3. BACKEND ARCHITECTURE

### 3.1 Logical Architecture

```text
                         ┌──────────────────────┐
                         │       Clients        │
                         │ Web / Mobile / CLI   │
                         └──────────┬───────────┘
                                    │ HTTPS
                                    ▼
                         ┌──────────────────────┐
                         │      FastAPI         │
                         │      /api/v1         │
                         │                      │
                         │ Routes / Controllers │
                         │ Authentication       │
                         │ Authorization        │
                         │ Request Validation   │
                         │ Response Contracts   │
                         └──────────┬───────────┘
                                    │
                                    ▼
              ┌────────────────────────────────────────┐
              │          Application Services          │
              │                                        │
              │ Profile Service                         │
              │ Job Service                             │
              │ Matching Service                        │
              │ CV Tailoring Service                    │
              │                                        │
              │ Matching Scoring Engine                 │
              └──────────────┬──────────────┬──────────┘
                             │              │
                 ┌───────────┘              └────────────┐
                 ▼                                       ▼
       ┌───────────────────┐                  ┌────────────────────┐
       │ Infrastructure    │                  │ Background Tasks   │
       │                   │                  │                    │
       │ PostgreSQL        │                  │ Profile extraction │
       │ Azure Blob        │                  │ Profile merge      │
       │ Authentication    │                  │ Job normalization  │
       │ AI providers      │                  │ Matching           │
       └───────────────────┘                  │ CV generation      │
                                              └─────────┬──────────┘
                                                        │
                                                        ▼
                                              ┌────────────────────┐
                                              │ External AI        │
                                              │ Provider           │
                                              │                    │
                                              │ OpenAI (V1)        │
                                              │ Other provider     │
                                              │ adapters (future)  │
                                              └────────────────────┘
```

### 3.2 API Layer

The API layer is responsible for HTTP routing, request validation, response serialization, authentication, authorization, API versioning, HTTP status codes, error translation, request correlation, and OpenAPI documentation.

The API layer must not contain business rules such as matching score calculation or profile consolidation logic.

### 3.3 Application Layer

Application services orchestrate use cases and coordinate infrastructure dependencies.

Current services:

- `ProfileService`
- `JobService`
- `MatchingService`
- `CVTailoringService`

Cross-cutting application concerns include authorization policies, transaction coordination, processing status management, and deterministic matching scoring.

### 3.4 Infrastructure Layer

Infrastructure adapters provide access to PostgreSQL, Azure Blob Storage, LLM provider APIs, authentication, configuration, and secrets.

Application services should depend on abstractions/interfaces rather than directly coupling business logic to infrastructure implementations.

---

## 4. TECHNOLOGY STACK

### 4.1 Current / V1 Backend Stack

| Area | Technology | Version / Baseline | Status | Purpose |
|---|---|---|---|---|
| Language | Python | 3.11+ | **Current** | Backend implementation |
| API Framework | FastAPI | 0.104+ | **Current** | REST API |
| Validation | Pydantic | 2.x | **Current** | Request/response validation |
| ORM / Data Access | SQLAlchemy | 2.x | **Current** | PostgreSQL access |
| Database | PostgreSQL | 15+ | **Current** | Persistent structured data |
| Database Migration | Alembic | 1.12+ | **Current** | Schema versioning |
| Containerization | Docker | Current stable | **Current** | Consistent runtime |
| Object Storage | Azure Blob Storage | Managed service | **Current** | User files and generated CVs |
| LLM Provider | OpenAI API | Configurable | **Current** | AI processing |
| API Documentation | OpenAPI / FastAPI | Built-in | **Current** | API contract/documentation |
| Testing | pytest | Current stable | **Current** | Automated testing |
| Static Analysis | mypy / Ruff or equivalent | Current stable | **Current** | Code quality |

### 4.2 Coming Soon / Future Technology

| Area | Technology | Status | Purpose |
|---|---|---|---|
| Authentication | Keycloak / OAuth2/OIDC | **Coming Soon** | External identity management |
| Distributed Background Processing | Celery | **Coming Soon** | Distributed worker execution |
| Queue / Broker | Redis | **Coming Soon** | Distributed task coordination |
| API Gateway | Azure API Management | **Coming Soon** | Gateway, policies, rate limiting |
| Secrets | Azure Key Vault | **Coming Soon** | Managed secret storage |
| Container Orchestration | Kubernetes | **Future** | Multi-instance orchestration |
| Metrics | Prometheus | **Future** | Advanced metrics |
| Distributed Tracing | OpenTelemetry | **Future** | Cross-component tracing |
| Advanced Monitoring | Azure Monitor / Log Analytics | **Coming Soon** | Cloud monitoring and alerting |
| Distributed Cache | Redis | **Future** | Application caching |
| Advanced Search | PostgreSQL FTS / Elasticsearch | **Future** | Advanced job search |

Future technologies are not required dependencies for the current V1 implementation.

---

## 5. API ARCHITECTURE

### 5.1 API Versioning

All public API endpoints use the `/api/v1` prefix.

Example:

```text
/api/v1/profile
/api/v1/jobs
/api/v1/matching
/api/v1/cv
```

A future incompatible API contract may be introduced under `/api/v2`.

### 5.2 API Capability Boundaries

#### Profile API

```text
POST   /api/v1/profile/sessions
POST   /api/v1/profile/sessions/{sessionId}/files
GET    /api/v1/profile/sessions/{sessionId}
GET    /api/v1/profile
PUT    /api/v1/profile
```

#### Job API

```text
POST   /api/v1/jobs/normalize
GET    /api/v1/jobs
GET    /api/v1/jobs/{jobId}
POST   /api/v1/jobs/{jobId}/interest
DELETE /api/v1/jobs/{jobId}
```

#### Matching API

```text
POST   /api/v1/matching
GET    /api/v1/matching/reports
GET    /api/v1/matching/reports/{reportId}
DELETE /api/v1/matching/reports/{reportId}
```

#### CV API

```text
POST   /api/v1/cv/tailor
GET    /api/v1/cv
GET    /api/v1/cv/{cvId}
GET    /api/v1/cv/{cvId}/download
DELETE /api/v1/cv/{cvId}
```

### 5.3 HTTP Status Conventions

| Situation | Status |
|---|---:|
| Successful GET / operation | 200 |
| Resource created | 201 |
| Long-running operation accepted | 202 |
| Validation failure | 400 / 422 |
| Authentication failure | 401 |
| Authorization failure | 403 |
| Resource not found | 404 |
| Duplicate / business conflict | 409 |
| Rate limit exceeded | 429 |
| External dependency unavailable | 503 |
| Unexpected server error | 500 |

### 5.4 API Error Contract

Errors returned to clients must use a consistent structure.

Example:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource was not found.",
    "details": null,
    "request_id": "abc-123"
  }
}
```

Internal implementation details, credentials, SQL statements, provider errors, and stack traces must never be exposed through the API.

---

## 6. AUTHENTICATION AND AUTHORIZATION

### 6.1 Current Authentication

V1 uses application-managed authentication with credentials stored in the application database.

The API:

1. receives credentials;
2. validates the account;
3. verifies the password hash;
4. issues an access token;
5. validates the token on subsequent requests.

Authentication implementation must remain isolated from business services.

### 6.2 Authorization

Authorization is based on the authenticated user identity and application permissions.

Core rule:

> A user may access only resources belonging to that user unless an explicitly authorized administrative operation permits otherwise.

Authorization checks are required for profiles, profile sessions, uploaded files, job interests, match reports, tailored CVs, and generated download links.

Job deletion is restricted to the original submitter or an administrator.

### 6.3 Coming Soon: External Identity Provider

Authentication may be migrated to Keycloak using OAuth2/OIDC.

The migration must not require changes to business services because those services consume an authenticated application identity rather than a specific authentication mechanism.

---

## 7. ASYNCHRONOUS PROCESSING

### 7.1 Current V1 Model

Long-running operations use **FastAPI BackgroundTasks**.

No distributed message broker or worker platform is required for V1.

Current background operations:

- profile document extraction
- profile consolidation
- job normalization
- matching
- CV tailoring

### 7.2 Processing Pattern

The API should validate the request, persist the processing request/state, start the background task, return `202 Accepted`, allow the client to retrieve processing status, and persist the final result or failure.

Example:

```text
POST /api/v1/matching
        ↓
Validate request
        ↓
Create MatchReport
(status = Processing)
        ↓
Start FastAPI BackgroundTask
        ↓
Return 202 + report_id
        ↓
Background processing
        ├── LLM evaluation
        ├── deterministic scoring
        ├── result persistence
        └── report completion
```

### 7.3 Processing Status

Long-running operations must expose a lifecycle such as:

```text
Created → Processing → Completed
                    ↘ Failed
```

The API must persist failure state sufficiently for the client to understand that processing failed without exposing internal implementation details.

### 7.4 Coming Soon: Distributed Processing

When workload or reliability requirements justify it, background processing may evolve to:

```text
FastAPI
   ↓
Queue / Broker
   ↓
Celery Workers
```

This is not part of the current V1 deployment requirement.

---

## 8. AI / LLM ARCHITECTURE

### 8.1 Provider Abstraction

The application must not directly couple business services to OpenAI-specific APIs.

Conceptually:

```text
ProfileService
      ↓
ProfileExtractionAI
      ↓
LLM Provider Adapter
      ↓
OpenAI
```

The same pattern applies to profile consolidation, job normalization, matching, and CV tailoring.

### 8.2 Current AI Provider

OpenAI is the initial provider for V1.

The architecture must allow the provider to be replaced or extended without changing business logic.

### 8.3 AI Responsibilities

The LLM is responsible for AI-specific interpretation and generation.

Profile processing includes extraction of profile information, skills, work experience, education, certifications, and profile consolidation.

Job processing includes normalization of raw job content and extraction of requirements, skills, qualifications, and technical stack.

Matching uses the qualitative values `Yes`, `Partial`, and `No`, together with rationale and qualitative analysis.

CV tailoring selects, prioritizes, summarizes, and rephrases information from the canonical profile for the target job.

### 8.4 Backend Responsibilities

The backend remains authoritative for:

- schema validation
- business validation
- matching score calculation
- weight redistribution
- eligibility
- ranking
- authorization
- resource ownership
- processing state
- historical result persistence

The LLM must not calculate the final matching score.

### 8.5 No-Fabrication Rule

CV tailoring must use the canonical user profile as its source of truth.

The AI may select existing information, prioritize information, reorder information, summarize information, and rephrase information.

The AI must not invent unsupported skills, employers, projects, dates, certifications, responsibilities, achievements, education, or professional experience.

---

## 9. MATCHING SCORING ARCHITECTURE

### 9.1 Base Weights

| Group | Base Weight |
|---|---:|
| Required Qualifications | 35% |
| Required Skills | 40% |
| Desirable Qualifications | 10% |
| Desirable Skills | 10% |
| Technical Stack | 5% |
| **Total** | **100%** |

### 9.2 Item Scores

| LLM Result | Numeric Value |
|---|---:|
| Yes | 1.0 |
| Partial | 0.5 |
| No | 0.0 |

The LLM returns only the qualitative result. The backend converts it to a numeric value.

### 9.3 Missing Groups

If a job does not contain one or more matching groups, the missing group's weight is redistributed proportionally across the available groups.

Example:

```text
Available:
Required Skills = 40
Technical Stack = 5

Available total = 45

Effective weights:
Required Skills = 40 / 45 = 88.89%
Technical Stack = 5 / 45 = 11.11%
```

The effective weights always sum to 100%.

### 9.4 Eligibility

Required-skills eligibility is independent from the overall score.

If required skills exist:

```text
Required Skills Group Score >= 0.70
```

means the user satisfies the required-skills eligibility criterion.

If no required skills exist, the threshold is not evaluated.

### 9.5 Scoring Responsibility

```text
                 LLM
                  ↓
        Yes / Partial / No
                  ↓
        Backend Scoring Engine
                  ├── Group Score
                  ├── Eligibility
                  ├── Overall Score
                  └── Ranking
```

---

## 10. DATA ARCHITECTURE

### 10.1 PostgreSQL

PostgreSQL is the primary persistence layer for structured application data.

Core entities include:

- User
- UserProfile
- ProfileSession
- UserFile
- Job
- JobInterest
- MatchReport
- MatchResult
- CVRequest
- TailoredCV

### 10.2 Structured Data vs JSON

Core business attributes required for filtering, joining, authorization, scoring, lifecycle management, and indexing should be represented as explicit database fields.

JSON/JSONB may be used for flexible or AI-generated structures such as detailed AI analysis, evidence metadata, flexible profile sections, and provider-specific metadata.

### 10.3 Historical Match Reproducibility

A MatchReport represents the matching result at a specific point in time.

The stored result must not change because the user's profile or job changes later.

The result should preserve or reference:

- profile version
- job snapshot/version
- scoring model version
- matching rules version
- LLM evaluation
- calculated scores
- eligibility
- ranking

---

## 11. DATABASE RELATIONSHIPS

```text
User
 ├── UserProfile (1:1)
 ├── UserFile (1:N)
 ├── ProfileSession (1:N)
 ├── JobInterest (1:N)
 ├── MatchReport (1:N)
 ├── CVRequest (1:N)
 └── TailoredCV (1:N)

ProfileSession
 └── UserFile (1:N)

MatchReport
 └── MatchResult (1:N)
        └── Job (N:1)

CVRequest
 └── TailoredCV (1:N)
        ├── MatchResult (N:1)
        └── Job (N:1)
```

### 11.1 Important Constraints

- User email must be unique.
- Job URL must be unique for deduplication.
- A user cannot create duplicate interest records for the same job.
- Resources must be scoped to the owning user.
- Match results retain historical job context.
- Profile versions must support historical matching results.

---

## 12. FILE AND OBJECT STORAGE

### 12.1 Azure Blob Storage

Azure Blob Storage stores user-uploaded source documents and generated tailored CVs.

Storage is logically isolated by user.

Example:

```text
user-files/
    {user_id}/
        profile/
        cv/
```

### 12.2 Storage Access

Clients must not be allowed to arbitrarily specify storage paths.

The API authenticates the user, verifies resource ownership, resolves the corresponding storage object, and performs the requested operation.

### 12.3 Temporary Processing Files

Temporary files created during processing may be deleted after processing. This does not imply deletion of the user's source document.

```text
User source file
      ↓
Azure Blob Storage
      ↓
Temporary processing copy
      ↓
Processing
      ↓
Temporary copy deleted
```

### 12.4 Download Links

Generated CVs are accessed through temporary, time-limited download URLs.

The API must authorize the user before generating the URL.

Initial expiration: **1 hour**. The expiration should remain configurable.

---

## 13. PROFILE PROCESSING ARCHITECTURE

### 13.1 Processing Session

A Profile Processing Session groups the files that belong to a single profile-building operation.

```text
ProfileSession
      │
      ├── UserFile
      ├── UserFile
      ├── UserFile
      ↓
Fragments
      ↓
Profile Consolidation
      ↓
UserProfile Version
```

### 13.2 Processing Flow

```text
Upload file
    ↓
Store source file
    ↓
Create UserFile = Pending
    ↓
FastAPI BackgroundTask
    ↓
Extract profile fragment
    ↓
Validate extraction result
    ↓
Persist fragment
    ↓
Check session completion
    ↓
All files complete?
    ├── No → wait
    └── Yes
          ↓
      Consolidate
          ↓
      Save canonical profile
```

### 13.3 Profile Data Precedence

The canonical profile is authoritative.

Recommended precedence:

```text
User-edited
    >
User-confirmed
    >
Extracted
    >
Inferred
```

AI processing must not silently overwrite user-edited values.

### 13.4 Mixed-Language Processing

The profile processing pipeline must support documents containing different languages and mixed-language input.

---

## 14. JOB NORMALIZATION ARCHITECTURE

### 14.1 Processing Flow

```text
POST /api/v1/jobs/normalize
          ↓
Validate URL + content
          ↓
Check URL uniqueness
          ↓
Create processing state
          ↓
FastAPI BackgroundTask
          ↓
LLM normalization
          ↓
Schema validation
          ↓
Business validation
          ↓
Persist normalized Job
          ↓
Completed
```

### 14.2 Observation Date

The backend records the date/time when the job is observed/saved by the platform. This is distinct from the original posting date extracted from the source.

### 14.3 Deduplication

The job URL is the initial unique identifier for deduplication.

---

## 15. CV TAILORING ARCHITECTURE

### 15.1 Processing Flow

```text
POST /api/v1/cv/tailor
          ↓
Validate MatchResult IDs
          ↓
Load canonical profile
          ↓
Load MatchResults
          ↓
Load related jobs
          ↓
FastAPI BackgroundTask
          ↓
LLM Tailoring
          ↓
Validate TailorResponse
          ↓
Render Markdown
          ↓
Store CV
          ↓
Create TailoredCV
          ↓
Completed
```

### 15.2 Tailoring Modes

#### Per Job

One tailored CV is generated for each selected MatchResult/job.

#### Group All

One common tailored CV is generated using the selected jobs as the target set.

The generated content must remain grounded in the canonical profile.

---

## 16. TRANSACTION AND CONSISTENCY RULES

Database transactions should be used for operations that require atomic persistence.

Examples include creation and completion of processing resources, persistence of MatchReports and MatchResults, and persistence of TailoredCV records.

External LLM calls must not be held inside a database transaction.

General pattern:

```text
Persist state
   ↓
External processing
   ↓
Validate result
   ↓
Persist result transactionally
```

---

## 17. IDEMPOTENCY AND DUPLICATE PROCESSING

Operations that can be retried must avoid creating inconsistent duplicate business records.

Examples:

- Job URL uniqueness prevents duplicate normalized jobs.
- User/job uniqueness prevents duplicate interest records.
- Processing resource identifiers prevent accidental duplication of reports or CV requests.
- Background tasks must verify current resource state before applying completion updates.

---

## 18. ERROR HANDLING AND RETRIES

### 18.1 Error Categories

| Error | API Response | Logging |
|---|---:|---|
| Validation error | 400 / 422 | INFO / DEBUG |
| Authentication failure | 401 | WARN |
| Authorization failure | 403 | WARN |
| Resource not found | 404 | INFO |
| Duplicate/conflict | 409 | INFO |
| LLM/provider unavailable | 503 | ERROR |
| Database failure | 500 | ERROR |
| Unexpected failure | 500 | ERROR |
| Rate limit | 429 | INFO |

### 18.2 Background Task Failures

A background operation that fails must:

1. record the failure;
2. update the processing resource to `Failed`;
3. store a safe error message;
4. log technical details internally;
5. avoid exposing provider credentials or stack traces to clients.

Retry behavior should be limited to errors considered transient.

---

## 19. SECURITY ARCHITECTURE

### 19.1 Current Controls

| Control | Current Requirement |
|---|---|
| Password hashing | Secure password hashing |
| Access tokens | Short-lived authentication tokens |
| Input validation | Pydantic validation |
| SQL injection protection | SQLAlchemy parameterized queries |
| CORS | Configured allowed origins |
| File size validation | Maximum upload size |
| File type validation | Supported file types only |
| Authorization | Resource ownership checks |
| Secret redaction | Secrets excluded from logs |
| Error sanitization | No internal details exposed |
| HTTPS | Required outside local development |

### 19.2 File Upload Controls

Initial supported file types:

- PDF
- DOCX
- TXT

Initial maximum file size: **10 MB**.

The exact limits are configuration values rather than immutable architecture constraints.

---

## 20. CONFIGURATION AND SECRETS

### 20.1 Current

Local development may use environment variables and a `.env` file that is excluded from source control.

Configuration categories include:

```text
DATABASE_URL
SECRET_KEY
OPENAI_API_KEY
STORAGE_CONFIGURATION
ENVIRONMENT
```

`.env.example` may be committed as a template containing no real credentials.

### 20.2 Coming Soon

Production secret management should move to Azure Key Vault when the production deployment requires managed secret storage.

Application code must consume secrets through configuration abstractions rather than hard-coding them.

---

## 21. OBSERVABILITY

### 21.1 Health Endpoints

```text
GET /health
GET /ready
```

`/health` confirms that the API process is operational.

`/ready` verifies required dependencies needed for normal operation.

### 21.2 Structured Logging

Logs should contain, where applicable:

```json
{
  "timestamp": "2026-09-08T14:30:00Z",
  "level": "INFO",
  "service": "tip-api",
  "request_id": "abc-123",
  "user_id": "user-456",
  "endpoint": "/api/v1/jobs/normalize",
  "method": "POST",
  "status_code": 202,
  "duration_ms": 120,
  "message": "Job normalization started"
}
```

### 21.3 Sensitive Data

Logs must not contain passwords, access tokens, API keys, connection strings, or full authentication credentials.

Personal and business data should be minimized in logs.

### 21.4 Coming Soon

Advanced monitoring may introduce Azure Monitor, Log Analytics, Prometheus, OpenTelemetry, distributed tracing, and alerting.

These are not required for the initial backend implementation.

---

## 22. PERFORMANCE AND SCALABILITY

### 22.1 Current V1

The V1 architecture is designed for a single API instance with FastAPI background processing.

Performance measures include database connection pooling, indexed queries, pagination, asynchronous I/O, bounded request payloads, efficient JSONB usage where appropriate, and batch processing inside background operations.

### 22.2 API Scaling

The API should remain stateless so that multiple instances can be introduced later without changing application behavior.

### 22.3 Coming Soon

When scale requires it, multiple API instances, distributed worker processes, queue/broker infrastructure, and distributed rate limiting may be introduced.

---

## 23. RATE LIMITING

Rate limiting is configurable by environment and endpoint category.

Initial categories:

| Category | Initial Guidance |
|---|---|
| General API | Configurable |
| Authentication | Strict per-IP limit |
| File uploads | Per-user limit |
| Matching | Dedicated computational limit |
| CV generation | Dedicated computational limit |

Matching and CV generation receive dedicated limits because they invoke potentially expensive AI processing.

Exact numerical limits belong in environment configuration rather than the architecture contract.

---

## 24. DEPLOYMENT ARCHITECTURE

### 24.1 Current V1

```text
                    Azure
                      │
              ┌───────┴────────┐
              │                │
        FastAPI API       PostgreSQL
              │
              │
       Azure Blob Storage
              │
              │
        OpenAI API
```

The application is containerized with Docker.

### 24.2 Development Environment

Development may use:

```text
Docker Compose
    ├── FastAPI
    └── PostgreSQL
```

Redis and distributed workers are not required for V1.

### 24.3 Production Baseline

The initial production deployment requires:

- containerized FastAPI application
- managed PostgreSQL
- Azure Blob Storage
- LLM provider access
- secure environment configuration
- HTTPS
- health/readiness checks

---

## 25. CI/CD AND QUALITY GATES

The backend pipeline should include:

```text
Commit
  ↓
Static analysis
  ↓
Unit tests
  ↓
API tests
  ↓
Integration tests
  ↓
Security checks
  ↓
Docker build
  ↓
Deployment
```

### 25.1 Required Tests

#### Unit Tests

Focus on matching score calculation, weight redistribution, eligibility, authorization rules, business rules, and state transitions.

#### API Tests

Focus on request validation, authentication, authorization, status codes, response contracts, and ownership rules.

#### Integration Tests

Focus on PostgreSQL, persistence, Blob Storage abstraction, AI provider abstraction, and background processing.

#### End-to-End Test

At least one complete backend flow should be covered:

```text
Profile upload
    ↓
Profile extraction
    ↓
Profile consolidation
    ↓
Job normalization
    ↓
Matching
    ↓
CV tailoring
```

---

## 26. DATABASE MIGRATION STRATEGY

Alembic manages schema migrations.

Requirements:

- migrations are versioned;
- migrations are stored in source control;
- schema changes are reviewed;
- migrations are backward-compatible where deployment sequencing requires it;
- data migrations are handled explicitly;
- destructive schema changes are controlled.

Database rollback must not be assumed to be safe after production data changes. Forward-compatible migration strategies are preferred.

---

## 27. CURRENT VS COMING SOON SUMMARY

### Current V1 — Required

```text
Python 3.11+
FastAPI
Pydantic
SQLAlchemy
Alembic
PostgreSQL
Azure Blob Storage
OpenAI
FastAPI BackgroundTasks
Docker
Versioned REST API
Application-managed authentication
Resource-level authorization
Structured logging
Health/readiness endpoints
pytest-based testing
Deterministic backend scoring
```

### Coming Soon

```text
Keycloak / OIDC
Celery
Redis broker
Azure API Management
Azure Key Vault
Advanced Azure monitoring
```

### Future

```text
Kubernetes
Multiple API instances
Distributed workers
Prometheus
OpenTelemetry
Distributed caching
Advanced search / Elasticsearch
ML-based matching
Automated job ingestion
```

---

## 28. ARCHITECTURAL BOUNDARIES

The following boundaries are mandatory for maintainability.

### API Boundary

The API handles HTTP concerns, not business calculations.

### Application Boundary

Application services orchestrate use cases and business operations.

### AI Boundary

AI providers return structured AI results; they do not own deterministic business rules.

### Scoring Boundary

The backend scoring engine owns numeric conversion, group scoring, effective weights, eligibility, overall score, and ranking.

### Persistence Boundary

Repositories/data-access components isolate database implementation from business logic.

### Storage Boundary

Blob Storage access is performed through an application-controlled storage abstraction.

### Authentication Boundary

Business services consume authenticated identity and permissions rather than depending on a specific authentication provider.

---

## 29. REFERENCE BACKEND PROJECT STRUCTURE

A logical project structure should reflect the architecture:

```text
src/
├── api/
│   ├── routes/
│   │   ├── profile.py
│   │   ├── jobs.py
│   │   ├── matching.py
│   │   └── cv.py
│   ├── dependencies/
│   └── error_handlers/
│
├── application/
│   ├── profile/
│   ├── jobs/
│   ├── matching/
│   └── cv/
│
├── domain/
│   ├── profile/
│   ├── jobs/
│   ├── matching/
│   └── cv/
│
├── infrastructure/
│   ├── database/
│   ├── storage/
│   ├── ai/
│   └── authentication/
│
├── background/
│   ├── profile_tasks.py
│   ├── job_tasks.py
│   ├── matching_tasks.py
│   └── cv_tasks.py
│
├── schemas/
├── configuration/
└── main.py
```

This structure is logical rather than prescriptive. The implementation may adapt the exact package organization while preserving the architectural boundaries.

---

## 30. FUTURE EVOLUTION

The architecture intentionally supports incremental evolution.

### Current

```text
FastAPI
   │
   ├── Application Services
   ├── PostgreSQL
   ├── Azure Blob
   ├── OpenAI
   └── BackgroundTasks
```

### Coming Soon

```text
FastAPI
   │
   ├── Application Services
   ├── PostgreSQL
   ├── Azure Blob
   ├── AI Provider Abstraction
   ├── Keycloak
   └── Celery + Redis
```

### Future Scale

```text
API Gateway
      │
      ▼
Multiple FastAPI instances
      │
      ├── PostgreSQL
      ├── Blob Storage
      ├── Distributed workers
      ├── AI providers
      └── Observability platform
```

Evolution should be driven by actual product usage, reliability, security, and scalability requirements rather than introducing infrastructure prematurely.

---

## 31. ARCHITECTURAL DECISIONS

| Decision | V1 Choice | Reason |
|---|---|---|
| API framework | FastAPI | Strong fit for Python async API and OpenAPI |
| Database | PostgreSQL | Reliable relational persistence and JSONB support |
| ORM | SQLAlchemy | Database abstraction and transaction management |
| API versioning | `/api/v1` | Clear API evolution path |
| Background processing | FastAPI BackgroundTasks | Sufficient for current V1 scope |
| Distributed queue | Deferred | Not required for current workload |
| LLM provider | OpenAI | Initial AI provider |
| LLM abstraction | Required | Avoid provider lock-in |
| Matching score | Backend | Deterministic and reproducible |
| Authentication | Application-managed | Aligns with current V1 requirement |
| External identity provider | Keycloak later | Planned authentication evolution |
| Object storage | Azure Blob | User document and generated CV storage |
| Containerization | Docker | Consistent deployment |
| Kubernetes | Deferred | No current need for orchestration complexity |
| API Gateway | Deferred | No current requirement for a gateway layer |

---

## 32. TRACEABILITY TO FUNCTIONAL SPECIFICATION

The backend architecture maps directly to the four functional capabilities:

| Functional Capability | Backend Components |
|---|---|
| Profile Processing | Profile API, Profile Service, Profile AI, BackgroundTasks, PostgreSQL, Blob Storage |
| Job Normalization | Job API, Job Service, Job AI, BackgroundTasks, PostgreSQL |
| Intelligent Matching | Matching API, Matching Service, Matching AI, Scoring Engine, BackgroundTasks, PostgreSQL |
| CV Tailoring | CV API, CV Tailoring Service, Tailoring AI, BackgroundTasks, PostgreSQL, Blob Storage |

The functional specification remains authoritative for product behavior and business requirements.

This technical specification defines how those requirements are supported by the backend architecture.

---

## 33. VERSION HISTORY

| Version | Date | Changes |
|---|---|---|
| 1.0 | Previous | Initial technical architecture |
| 1.1 | 2026-09-08 | Backend-focused revision; separated current and future requirements; retained FastAPI BackgroundTasks for V1; clarified API boundaries, AI abstraction, deterministic matching/scoring, authentication abstraction, storage security, async processing, testing, and deployment boundaries |

---

*This document defines the technical architecture baseline for the Talent Intelligence Platform V1.1 backend/API. Future technologies identified as Coming Soon or Future are intentionally excluded from the current implementation baseline unless separately approved.*
