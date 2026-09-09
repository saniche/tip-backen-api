# Research: Talent Intelligence Platform

## Decisions

### V1 processing model

**Decision**: Persist a processing resource, schedule the operation with FastAPI BackgroundTasks, return `202 Accepted`, and expose the resource status for polling.

**Rationale**: Profile extraction, job normalization, matching, and CV tailoring may call an AI provider and exceed request-response latency. The V1 scope uses a single service instance, so a distributed queue is unnecessary.

**Alternatives considered**: Synchronous requests hold client connections during long work. Celery and Redis add distributed infrastructure outside V1 scope.

### Data and historical results

**Decision**: Store searchable, joinable, and authorization fields as relational columns; store flexible AI evidence and analysis in JSON. Persist profile and job context, scoring/rules version, AI assessment, scores, eligibility, and rank with each match result.

**Rationale**: This preserves report reproducibility when a profile or job later changes while allowing structured filtering and ownership enforcement.

**Alternatives considered**: A fully JSON model weakens constraints and queries. Recalculating reports on read would allow historical results to drift.

### Match scoring

**Decision**: AI returns only `Yes`, `Partial`, or `No` plus rationale. Backend code maps those to 1.0, 0.5, and 0.0, redistributes missing-group weights proportionally, determines required-skill eligibility at 0.70, calculates overall scores, and ranks results.

**Rationale**: Deterministic rules are testable, explainable, and cannot vary with provider output.

**Alternatives considered**: AI-calculated numeric scores make the business outcome non-deterministic.

### Security, storage, and AI boundaries

**Decision**: Use application-managed hashed credentials and short-lived access tokens in V1; authorize every owned resource before data access or download. Store files through an application-controlled Azure Blob Storage abstraction. Define structured AI interfaces for extraction, consolidation, normalization, qualitative matching, and CV tailoring.

**Rationale**: This meets V1 security requirements while keeping business services independent of future identity providers and OpenAI-specific implementation details.

**Alternatives considered**: Direct client blob paths and provider calls in route handlers bypass ownership controls and mix transport, business, and provider concerns.
