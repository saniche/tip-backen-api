# Research: Structured AI Processing

## Decision: Use strict JSON Schema output through the existing OpenAI HTTP helper

**Rationale**: The repository already provides `call_openai_structured` in `llm_structured.py`.
It derives JSON Schema from a Pydantic v2 model and calls OpenAI Chat Completions with strict
JSON-schema output. This meets the typed-output requirement without a second client or duplicated
schema definitions.

**Alternatives considered**:

- Adopt the OpenAI Python SDK Responses API: official guidance supports it, but it adds a
  dependency and replaces an existing provider boundary without a feature need.
- Use JSON mode: rejected because it guarantees JSON syntax, not canonical-shape compliance.
- Retain local heuristics: rejected because they cannot reliably interpret unstructured content.

## Decision: Define one strict Pydantic model per processing operation

**Rationale**: Profile extraction, job normalization, match assessment, and CV tailoring have
different semantics and consumers. Each schema uses `extra="forbid"`, an object root, required
fields, nullable scalars for absent data, and empty lists for absent collections. This complies
with Structured Outputs requirements and prevents schema drift.

**Alternatives considered**:

- Reuse JSON persistence dictionaries as schemas: rejected because they lack explicit validation.
- Use a generic dictionary schema: rejected because it cannot prevent malformed downstream data.

## Decision: Configure a distinct model identifier for each operation

**Rationale**: Separate configuration values allow profile, normalizer, matching, and CV tasks to
evolve independently while sharing the HTTP client. Begin with a strict-structured-output-capable
`gpt-4o-mini`-or-later model; pin approved production snapshots after quality evaluation.

**Alternatives considered**:

- Use one hard-coded model: rejected because it prevents operation-specific quality and cost tuning.

## Decision: Preserve public routes and existing processing states

**Rationale**: Profile, normalization, and CV workflows already use background tasks and can await
provider calls. Matching becomes asynchronous internally and commits only after every selected job
assessment validates. No public API or database migration is needed.

**Alternatives considered**:

- Convert matching to a background processing resource: rejected because it changes the route contract.
- Call async code through blocking wrappers: rejected because it complicates task lifecycle handling.

## Decision: Translate provider failures at one boundary; do not auto-retry initially

**Rationale**: Missing configuration, transport failure, timeout, non-success response, refusal,
incomplete output, and validation failure become local safe exceptions. Existing workers keep their
generic failed statuses; matching returns the current safe service-unavailable error. Retry is
deferred to avoid hidden cost and nested retry multiplication.

**Alternatives considered**:

- Expose raw provider exceptions: rejected because they can reveal provider details or source data.
- Retry all errors: rejected because schema, configuration, and refusal failures are non-transient.

## Decision: Mock the shared helper in normal tests

**Rationale**: Tests remain deterministic, offline, and secret-free by replacing the helper with
async fakes that return typed models or raise local provider exceptions. A separately gated staging
smoke test may use sanitized inputs and an approved key.

**Alternatives considered**:

- Live provider calls in pytest: rejected due to cost, nondeterminism, and secret exposure.

## Sources

- [OpenAI Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Repository OpenAI helper](../../llm_structured.py)
- [Feature specification](spec.md)