<!--
Sync Impact Report
Version change: unversioned template -> 1.0.0
Modified principles: none; initial adoption
Added sections: Core Principles, Service Constraints, Development Workflow, Governance
Removed sections: none
Follow-up TODOs: none
-->

# Job Process API Constitution

## Core Principles

### I. Clear Service Contracts

Every public endpoint, request model, response model, and error response MUST have a clear,
documented purpose. Contract changes MUST preserve compatibility or be explicitly versioned and
communicated. Clear contracts make the API predictable for its consumers.

### II. Test by Design

New behavior MUST include automated tests designed with the behavior, not added as an afterthought.
Tests MUST cover the intended result, validation failures, and relevant edge cases. A change is not
complete until its focused tests pass; this keeps the service safe to evolve.

### III. Verify Integration Boundaries

Changes to routers, persistence, authentication, external HTTP calls, blob storage, or LLM output
MUST include integration or contract tests at the affected boundary. External dependencies MUST be
isolated behind testable interfaces where practical. Boundary tests catch failures unit tests
cannot.

### IV. Reuse Deliberately

Shared business rules, schemas, serialization, and infrastructure access MUST live in reusable
modules with one clear responsibility. New code MUST reuse an existing abstraction when it meets the
need; otherwise, duplication requires a short justification. This prevents routes from drifting into
inconsistent implementations.

### V. Keep Delivery Simple and Observable

Implement the smallest solution that satisfies the defined requirement. Production paths MUST emit
actionable errors and preserve enough context to diagnose failures without exposing secrets or
personal data. Simplicity and observability reduce operational cost.

## Service Constraints

The service MUST retain FastAPI, Pydantic, and SQLAlchemy conventions unless a deliberate,
documented migration is approved. Authentication, authorization, input validation, and secret
handling MUST be addressed for every externally reachable feature. Sensitive data MUST NOT be
written to logs, error responses, or committed configuration.

## Development Workflow

Each change MUST begin with a defined behavior and acceptance criteria. Implementers MUST add or
update focused tests, run the relevant test suite, and review API, schema, migration, and security
impact before merge. Code review MUST verify constitution compliance and require an explicit
exception rationale when a principle cannot be met.

## Governance

This constitution supersedes conflicting development practices. Amendments MUST document the
reason, affected principles, migration impact, and semantic version bump. A MAJOR version removes
or redefines a governing rule incompatibly; a MINOR version adds a principle or materially expands
guidance; a PATCH version clarifies wording without changing intent. Every review MUST assess
compliance, and approved exceptions MUST be time-bound and recorded with the relevant change.

**Version**: 1.0.0 | **Ratified**: 2026-09-08 | **Last Amended**: 2026-09-08
