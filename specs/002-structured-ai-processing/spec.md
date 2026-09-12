# Feature Specification: Structured AI Processing

**Feature Branch**: `002-structured-ai-processing`

**Created**: 2026-09-11

**Status**: Draft

**Input**: User description: "use llm(openai) to process unstruture data for this processes, profile builder, jobNormalizer, jobMatching and cv tailoring. The llm ouput should be strutured json, to fit the model. Now the output can be use fro subsecant process or action."

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Build a Reliable Candidate Profile (Priority: P1)

As a job seeker, I want my uploaded unstructured resume to be converted into a complete, structured profile so that subsequent matching and document tailoring use accurate information.

**Why this priority**: A structured candidate profile is the foundation for matching and tailored document generation.

**Independent Test**: Upload a resume containing contact details, skills, work history, education, languages, and certifications, then verify the resulting profile contains valid, typed values for the available information.

**Acceptance Scenarios**:

1. **Given** an authenticated user submits a supported resume with recognisable profile details, **When** profile processing completes, **Then** the user can retrieve a structured profile containing the extracted information in the expected fields.
2. **Given** a resume omits an optional profile detail, **When** profile processing completes, **Then** the profile remains valid and represents the missing detail without inventing a value.
3. **Given** profile interpretation cannot produce a valid structured result, **When** processing completes, **Then** the processing result is marked failed with a safe, actionable message and no partial invalid profile becomes current.

---

### User Story 2 - Structure a Job Posting for Matching (Priority: P1)

As a job seeker, I want an unstructured job posting converted into consistent job requirements so that the platform can evaluate it against my profile.

**Why this priority**: Reliable job structure is required for meaningful, repeatable match results.

**Independent Test**: Submit a job posting with responsibilities, required skills, preferred skills, and qualifications, then verify the completed job contains each available category in its defined structure.

**Acceptance Scenarios**:

1. **Given** an authenticated user submits a job posting, **When** processing completes, **Then** the job contains structured responsibilities, requirements, preferences, and technical skills suitable for matching.
2. **Given** a posting contains no explicit preferred qualifications, **When** processing completes, **Then** the job is valid and its preferred-qualification collection is empty.
3. **Given** job interpretation returns malformed or incomplete required structure, **When** processing completes, **Then** the job processing result is marked failed and the malformed result is not made available for matching.

---

### User Story 3 - Receive Explainable Structured Match Results (Priority: P2)

As a job seeker, I want my profile compared with structured job requirements so that I can understand my eligibility, score, gaps, and rationale for each job.

**Why this priority**: Matching is the user-facing decision support outcome built from the profile and job structure.

**Independent Test**: Create a profile and job with overlapping and non-overlapping requirements, request a match, and verify every requirement group contains structured assessments that downstream scoring can consume.

**Acceptance Scenarios**:

1. **Given** a user has a current profile and a structured job, **When** the user requests matching, **Then** the result contains structured assessments for required and preferred qualifications, skills, and technical stack, plus an explanation.
2. **Given** the profile lacks a required skill, **When** matching completes, **Then** that assessment identifies the gap rather than claiming the skill is present.
3. **Given** structured matching output fails validation, **When** a match is requested, **Then** no misleading result is persisted and the user receives a safe failure response.

---

### User Story 4 - Generate a Tailored CV from Structured Context (Priority: P2)

As a job seeker, I want a tailored CV generated from my profile, selected job, and match result so that the document is specific to the target role while remaining grounded in my experience.

**Why this priority**: Tailored output turns the profile and match analysis into a usable application artifact.

**Independent Test**: Request a tailored CV for a completed match and verify the completed document contains a structured role, summary, experience, education, certifications, and skills drawn from the matching context.

**Acceptance Scenarios**:

1. **Given** a user selects a completed match, **When** CV tailoring completes, **Then** the user can retrieve a document built from a valid structured result.
2. **Given** the selected profile does not contain education or certifications, **When** tailoring completes, **Then** the document remains valid and omits or leaves empty only those unavailable sections.
3. **Given** document tailoring cannot produce a valid structured result, **When** processing completes, **Then** the processing result is marked failed and no incomplete document is published.

### Edge Cases

- An input contains French, English, or mixed-language content; available facts are preserved in the structured result without translation unless the user requested an output language.
- The interpretation service is unavailable, times out, or returns no usable result; the affected processing activity fails safely and can be retried without corrupting prior completed data.
- The interpretation service returns syntactically valid data that does not satisfy the expected shape; the result is rejected before persistence or downstream use.
- Input includes instructions intended to override the requested extraction task; only information relevant to the requested structured fields is used.
- A candidate submits sensitive contact details; these remain accessible only through the candidate's authorized profile and are not exposed in failure messages or logs.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: The system MUST interpret unstructured candidate documents into the complete canonical profile shape, using only facts supported by the submitted document.
- **FR-002**: The system MUST interpret unstructured job postings into the canonical job shape, including responsibilities, required qualifications and skills, preferred qualifications and skills, and technical stack when present.
- **FR-003**: The system MUST validate every interpreted result against the corresponding canonical data shape before it is persisted or supplied to another process.
- **FR-004**: The system MUST reject interpreted results that are missing required fields, contain values of an incompatible type, or otherwise fail the canonical shape validation.
- **FR-005**: The system MUST preserve valid empty values for optional information rather than inventing unsupported facts.
- **FR-006**: The system MUST produce structured per-requirement assessments for matching that identify support, partial support, or absence and include a rationale grounded in the profile and job context.
- **FR-007**: The system MUST derive matching scores and eligibility only from validated structured matching assessments.
- **FR-008**: The system MUST produce a structured tailored-CV result from the selected profile, job, and match context before rendering or publishing the document.
- **FR-009**: The system MUST ensure each tailored-CV statement is grounded in the selected profile and job context; it MUST NOT add unsupported experience, qualifications, skills, credentials, or achievements.
- **FR-010**: The system MUST record a safe failed processing state when interpretation fails, is unavailable, exceeds its allowed processing time, or returns an invalid result.
- **FR-011**: The system MUST retain the last successfully completed profile, job, match report, or tailored CV when a later processing attempt fails.
- **FR-012**: The system MUST return safe, actionable failures to authorized users without exposing service credentials, raw provider responses, or personal data beyond the request context.
- **FR-013**: The system MUST support downstream profile, matching, scoring, and document-generation actions using only validated structured outputs.
- **FR-014**: The system MUST provide automated coverage for successful interpretation, invalid structured output, provider unavailability, and unsupported-fact prevention for each of the four processing activities.

### Key Entities _(include if feature involves data)_

- **Structured Profile**: The validated representation of a candidate's identity, summary, skills, experience, education, languages, certifications, and preferences extracted from candidate-provided content.
- **Structured Job**: The validated representation of a job posting's role, responsibilities, required and preferred qualifications and skills, and technical context.
- **Match Assessment**: A validated, per-requirement comparison of profile evidence to a job requirement, including result and rationale, used to derive a score and eligibility.
- **Structured Tailored CV**: A validated role-specific document representation containing only facts grounded in the candidate profile and selected job context.
- **Processing Result**: The observable state of an interpretation activity, including its completion outcome, usable result reference when successful, and safe failure information when unsuccessful.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: In a representative acceptance set of 50 resumes, at least 95% produce a valid profile result or a clearly failed processing result, with no malformed profile made available to users.
- **SC-002**: In a representative acceptance set of 50 job postings, at least 95% produce a valid job result or a clearly failed processing result, with no malformed job made available for matching.
- **SC-003**: 100% of accepted profile, job, matching, and tailored-CV results satisfy their defined canonical structure before downstream use.
- **SC-004**: In acceptance tests containing deliberately unsupported candidate facts, 100% of tailored CVs omit the unsupported facts.
- **SC-005**: At least 95% of completed profile, job, match, and tailored-CV processing requests expose a final outcome to the requesting user within 60 seconds under normal operating conditions.
- **SC-006**: All defined provider-unavailability and invalid-output scenarios result in a safe failure state and preserve the user's last successful completed data.

## Assumptions

- The existing authenticated ownership model continues to govern access to submitted content and all derived results.
- The existing canonical profile, job, matching, and tailored-CV shapes are the authoritative contracts; this feature does not redefine their public fields unless a separately approved contract change is needed.
- Candidate documents and job postings may be in French, English, or a mixture of both.
- Processing operations may continue asynchronously, and users can inspect the existing processing status resource for completion or failure.
- The external interpretation provider is configured in each environment and its credentials are managed outside source control.
- This feature covers structured interpretation and validation for the four named processes; changes to authentication, user interface, retention policy, and unrelated job lifecycle operations are out of scope.
