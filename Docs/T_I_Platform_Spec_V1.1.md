# TALENT INTELLIGENCE PLATFORM

## COMPLETE FUNCTIONAL SPECIFICATION

---

## 1. OVERVIEW

### 1.1 Purpose

The Talent Intelligence Platform is a comprehensive system designed to
process and analyze talent-related data through intelligent automation.
The platform handles user profile extraction from heterogeneous
documents, job posting normalization, matching analysis between profiles
and job requirements, and tailored CV generation.

### 1.2 Core Capabilities

The platform delivers four primary capabilities:

| Capability | Description |

|------------|-------------|

| **Profile Processing** | Extracts and merges user profiles from
multiple document sources |

| **Job Normalization** | Converts raw job postings into
structured, searchable data |

| **Intelligent Matching** | Analyzes compatibility between user
profiles and job requirements |

| **CV Tailoring** | Generates customized CVs optimized for
specific job applications |

### 1.3 System Principles

| Principle | Description |

|-----------|-------------|

| **User Ownership** | All data belongs to and is controlled by
individual users |

| **Asynchronous Processing** | Long-running operations (LLM
processing) execute in background queues |

| **Structured Data** | All extracted information follows
standardized schemas |

| **Cloud-Native Architecture** | Designed for cloud deployment
with containerized storage |

---

## 2. USER DOMAIN

### 2.1 User Entity

The User serves as the root identity for all platform operations.

#### 2.1.1 Fields

| Field | Type | Description |

|-------|------|-------------|

| id | UUID | Unique identifier |

| email | String | User's email address (must be unique) |

| hashed_password | String | Securely hashed password |

| created_at | Datetime | Account creation timestamp |

| role | Enum | User role (Standard or Admin) |

#### 2.1.2 Ownership Rules

| Owned Entity | Description |

|--------------|-------------|

| User Profile | The user's complete profile data |

| User Files | Files uploaded by the user (stored in their container)
|

| Match Reports | Reports generated from matching operations |

| Tailored CVs | Customized CV documents created by the system |

| Job Interests | Jobs marked as interesting by the user |

**Important:** Users can only access their own data. The Admin role
may perform system-level operations for maintenance purposes.

---

## 3. PROFILE DOMAIN

### 3.1 Contribution Level (Enumeration)

Contribution levels define a user's engagement with specific skills.

| Level | Multiplier | Description |

|-------|------------|-------------|

| Passive | ×0.5 | Minimal involvement |

| Support | ×0.75 | Supporting role |

| Active | ×1.0 | Active participation |

| Intensive | ×1.25 | Deep engagement |

### 3.2 Skill Entry

Represents a skill with associated experience metrics.

| Field | Type | Description |

|-------|------|-------------|

| name | String | Skill name |

| projects | List[String] | Related projects |

| experience_months | Integer | Raw experience in months |

| contribution | ContributionLevel | Contribution level |

| effective_experience_months | Double | Weighted experience |

| effective_experience_years | Double | Weighted experience in years
|

### 3.3 Work Experience

Structured representation of professional experience.

| Field | Type | Description |

|-------|------|-------------|

| job_title | String | Position title |

| company | String | Employer name |

| location | String | Work location |

| start_date | Date | Employment start date |

| end_date | Date | Employment end date |

| is_current | Boolean | Currently employed? |

| achievements | List[String] | Key accomplishments |

| responsibilities | List[String] | Role duties |

| technologies | List[String] | Technologies used |

### 3.4 Education

Formal education history.

| Field | Type | Description |

|-------|------|-------------|

| degree | String | Degree obtained |

| field | String | Field of study |

| institution | String | Educational institution |

| graduation_year | Integer | Year of graduation |

| location | String | Institution location |

| start_date | Date | Education start date |

| end_date | Date | Education end date |

### 3.5 User Profile (Canonical)

The master profile that merges all extracted data.

| Field | Type | Description |

|-------|------|-------------|

| name | String | Full name |

| email | String | Email address |

| phone | String | Contact number |

| location | String | Current location |

| summary | String | Professional summary |

| skills | List[SkillEntry] | All skills with metrics |

| technical_skills | List[String] | Technical skill names |

| soft_skills | List[String] | Soft skill names |

| languages | List[String] | Languages spoken |

| certifications | List[ProfileCertificate] | Professional
certifications |

| work_experiences | List[WorkExperience] | Employment history |

| education | List[Education] | Academic history |

| total_years_of_experience | Integer | Overall experience |

| preferred_job_titles | List[String] | Desired positions |

| preferred_locations | List[String] | Desired locations |

| raw_content | String | Original extracted text |

| raw_content_cv | String | Original CV content |

---

## 4. PROFILE EXTRACTION (LLM SCHEMAS)

### 4.1 Profile Certificate (LLM)

| Field | Type | Description |

|-------|------|-------------|

| name | String | Certification name |

| year | Integer | Year obtained |

### 4.2 Profile Work Experience (LLM)

Same structure as Work Experience.

### 4.3 Profile Education (LLM)

Same structure as Education.

### 4.4 Profile Raw Skill (LLM)

| Field | Type | Description |

|-------|------|-------------|

| name | String | Skill name |

| projects | List[String] | Related projects |

| experience_months | Integer | Experience in months |

| months_source | Enum | 'explicit' or 'estimated' |

| contribution | ContributionLevel | Contribution level |

### 4.5 Partial Profile Response (LLM)

Extracted from a single document.

| Field | Type | Description |

|-------|------|-------------|

| name | String | Full name |

| email | String | Email address |

| phone | String | Contact number |

| location | String | Location |

| linkedin | String | LinkedIn profile URL |

| summary | String | Professional summary |

| soft_skills | List[String] | Soft skills |

| languages | List[String] | Languages |

| certifications | List[ProfileCertificate] | Certifications |

| work_experiences | List[ProfileWorkExperience] | Work history |

| education | List[ProfileEducation] | Academic history |

| preferred_job_titles | List[String] | Desired positions |

| preferred_locations | List[String] | Desired locations |

| technical_skills | List[ProfileRawSkill] | Technical skills with
metrics |

### 4.6 Merged Profile Response (LLM)

Final merged profile.

| Field | Type | Description |

|-------|------|-------------|

| name | String | Full name |

| email | String | Email address |

| phone | String | Contact number |

| location | String | Location |

| linkedin | String | LinkedIn profile URL |

| summary | String | Professional summary |

| soft_skills | List[String] | Soft skills |

| languages | List[String] | Languages |

| certifications | List[ProfileCertificate] | Certifications |

| work_experiences | List[ProfileWorkExperience] | Work history |

| education | List[ProfileEducation] | Academic history |

| preferred_job_titles | List[String] | Desired positions |

| preferred_locations | List[String] | Desired locations |

---

## 5. JOB DOMAIN

### 5.1 Normalized Job

Structured job postings.

| Field | Type | Description |

|-------|------|-------------|

| job_number | String | Job identifier |

| job_title | String | Position title |

| company | String | Employer |

| location | String | Job location |

| job_id | String | External job ID |

| source | String | Where posted |

| url | String | Job posting URL (unique) |

| salary | String | Compensation |

| posted_date | Date | Original posting date |

| saved_date | Date | Date saved in system |

| summary | String | Job overview |

| key_responsibilities | List[String] | Core duties |

| required | List[String] | Required qualifications |

| desirable | List[String] | Nice-to-have qualifications |

| technical_stack | List[String] | Technologies used |

### 5.2 Job Listing (LLM)

LLM-extracted job data.

| Field | Type | Description |

|-------|------|-------------|

| title | String | Position title |

| posting_date | Date | When posted |

| company | String | Employer |

| location | String | Location |

| salary | String | Compensation |

| url | String | Posting URL |

| source | String | Posting source |

| summary | String | Job overview |

| key_responsibilities | List[String] | Core duties |

| required | JobRequirements | Required qualifications |

| desirable | JobRequirements | Desirable qualifications |

| technical_stack | List[String] | Technologies used |

### 5.3 Job Requirements Structure

| Field | Type | Description |

|-------|------|-------------|

| qualifications | List[String] | Educational/professional
requirements |

| skills | List[String] | Required skills |

### 5.4 Job Extraction (LLM)

Container for multiple job listings.

| Field | Type | Description |

|-------|------|-------------|

| jobs | List[JobListing] | Extracted job listings |

---

## 6. MATCHING DOMAIN

### 6.1 LLM Item Matching

Match result for a single item.

| Field | Type | Description |

|-------|------|-------------|

| item | String | Item being matched |

| match | Enum | 'Yes', 'Partial', or 'No' |

| comment | String | Detailed rationale |

### 6.2 LLM Match Response

Complete match analysis.

| Field | Type | Description |

|-------|------|-------------|

| required_qualifications | List[LlmItemMatching] | Qualification
matches |

| required_skills | List[LlmItemMatching] | Skill matches |

| desirable_qualifications | List[LlmItemMatching] | Desirable
qualification matches |

| desirable_skills | List[LlmItemMatching] | Desirable skill
matches |

| technical_stack | List[LlmItemMatching] | Technical stack matches
|

| ai_analysis | String | Overall match analysis |

---

## 7. TAILORED CV DOMAIN

### 7.1 Tailor Positioning

| Field | Type | Description |

|-------|------|-------------|

| role_line | String | Desired role |

| head_line | String | Professional headline |

### 7.2 Tailor Skill Group

| Field | Type | Description |

|-------|------|-------------|

| category | String | Skill category |

| skills | List[String] | Skills in this category |

### 7.3 Tailor Experience Content

| Field | Type | Description |

|-------|------|-------------|

| intro | String | Experience introduction |

| bullets | List[String] | Key achievements |

### 7.4 Tailor Response (LLM)

| Field | Type | Description |

|-------|------|-------------|

| selected_education_ids | List[String] | Education entries to
include |

| selected_certification_ids | List[String] | Certifications to
include |

| selected_experience_ids | List[String] | Experiences to include
|

| positioning | TailorPositioning | Role positioning |

| summary | String | Professional summary |

| core_competencies | List[String] | Key competencies |

| technical_skill_groups | List[TailorSkillGroup] | Skills by
category |

| competency_variant_used | String | Competency variation |

| experience_content | Map[String, TailorExperienceContent] |
Experience by ID |

### 7.5 Tailored CV (Final Model)

| Field | Type | Description |

|-------|------|-------------|

| header | String | CV header |

| positioning | TailorPositioning | Role positioning |

| summary | String | Professional summary |

| core_competencies | List[String] | Key competencies |

| technical_skills | List[TailorSkillGroup] | Technical skills |

| experience | List[TailorExperienceContent] | Experience details
|

| education | List[Education] | Education details |

| certifications | List[ProfileCertificate] | Certification details
|

| meta | Object | Metadata |

---

## 8. CANONICAL SKILL MAPPING

A dictionary mapping raw skill names to canonical skill names ensures
consistency across profiles and matches.

**Example:**

```

"js" → "JavaScript"

"react.js" → "React"

"node" → "Node.js"

"python" → "Python"

"aws" → "Amazon Web Services"

```

---

## 9. RELATIONSHIPS SUMMARY

```

┌─────────┐

│ User │

└────┬────┘

│

├─── UserProfile (1:1)

├─── UserFiles (1:N)

├─── JobInterests (1:N)

├─── MatchReports (1:N) ──── MatchResults (1:N) ──── Job (N:1)

└─── TailoredCVs (1:N) ──── TailoredCV (1:1)

```

| Relationship | Type | Description |

|--------------|------|-------------|

| User → UserProfile | 1:1 | Each user has one profile |

| User → UserFiles | 1:N | Each user can have multiple files |

| User → JobInterests | 1:N | Each user can mark multiple jobs as
interesting |

| User → MatchReports | 1:N | Each user can have multiple match
reports |

| MatchReport → MatchResults | 1:N | Each report has multiple job
match results |

| MatchResult → Job | N:1 | Many results can reference the same job
|

| User → TailoredCVs | 1:N | Each user can have multiple tailored CVs
|

| TailoredCV → TailoredCV | 1:1 | Final rendered CV document |

---

## 10. WORKFLOW SPECIFICATIONS

### 10.1 Profile Extraction Workflow

**Purpose:** Extract and merge user profile information from a defined set of document uploads.

**Profile Processing Session:**

A profile processing session groups the files intended to contribute to the same merge operation. A session may contain one or more files. This makes the V0 rule "when the last file is processed, merge" explicit and testable without implying that every future upload must automatically trigger a complete historical merge.

**Sequence:**

| Step | Action        | Description                                                               |
| ---- | ------------- | ------------------------------------------------------------------------- |
| 1    | Start Session | User starts a profile processing session                                  |
| 2    | Upload        | User uploads a file (CV, document, etc.) into the session                 |
| 3    | Storage       | File is stored in the user's isolated storage area                        |
| 4    | Record        | UserFile is created with `Pending` status and associated with the session |
| 5    | Process       | File is processed independently                                           |
| 6    | Extraction    | LLM extracts a PartialProfileResponse                                     |
| 7    | Save          | ProfileFragment is saved to the database                                  |
| 8    | Check         | System checks whether all files in the session have completed processing  |
| 9    | Merge         | When all session files are complete, the system requests a merged profile |
| 10   | Finalize      | Merged profile is saved as UserProfile                                    |

**Rules:**

- Each file is processed independently.
- A file may contribute partial information to the final profile.
- Final merge occurs only when all files belonging to the session have completed successfully.
- Mixed-language input documents are supported.
- `UserProfile` is the source of truth for matching and CV tailoring.
- User edits to the canonical profile must not be silently overwritten by later extraction or merge operations.

### 10.1.1 Profile Data Precedence

When information from different sources conflicts, the system preserves the user's authoritative information. The functional precedence is:

1. User-edited data
2. User-confirmed extracted data
3. Extracted profile data
4. AI-inferred data

The system must not replace a user-edited value with a newly inferred value without an explicit user action.

### 10.1.2 Profile Evidence

The profile should distinguish factual information supported directly by source documents from conclusions inferred by the LLM. This distinction is important for reliable matching and CV tailoring.

### 10.2 Job Normalization Workflow

**Purpose:** Convert raw job posting content into structured,
searchable data.

**Sequence:**

| Step | Action | Description |

|------|--------|-------------|

| 1 | Submission | User provides URL and raw content |

| 2 | Normalization | LLM normalizes job content |

| 3 | Extraction | LLM produces JobExtraction |

| 4 | Deduplication | System checks if URL already exists |

| 5 | Save | System saves Job with NormalizedJson |

| 6 | Record | ObservationDate is recorded |

**Rules:**

- URL serves as a unique key for deduplication

- ObservationDate is automatically recorded

- Only the submitter or system admin can delete jobs

**Filtering Options:**

| Filter | Description |

|--------|-------------|

| Date of Observation | Filter by when the job was saved |

| Title | Filter by job title |

| Company | Filter by employer name |

| Location | Filter by job location |

| **Default Ordering** | Observation date descending (newest
first) |

### 10.3 Matching Workflow

**Purpose:** Analyze compatibility between a user profile and
selected jobs.

**Sequence:**

| Step | Action | Description |

|------|--------|-------------|

| 1 | Selection | User selects job IDs to match against |

| 2 | Load Profile | System loads the user's UserProfile |

| 3 | Load Jobs | System loads the selected Jobs |

| 4 | Batch Analysis | LLM produces LlmMatchResponse per job |

| 5 | Create Report | System creates a MatchReport |

| 6 | Create Results | System creates MatchResult per job |

**Rules:**

- Each job is analyzed independently

- Results are ranked from highest to lowest match score

- Reports include matching date and user context

**Report Management:**

| Action | Description |

|--------|-------------|

| List Reports | View all match reports for the user |

| View Details | See ranked MatchResult (highest to lowest score) |

| Delete Report | User can delete any of their reports |

### 10.4 Tailored CV Workflow

**Purpose:** Generate customized CVs optimized for specific job
applications.

**Sequence:**

| Step | Action | Description |

|------|--------|-------------|

| 1 | Selection | User selects MatchResult IDs |

| 2 | Load Data | System loads UserProfile, MatchResults, and Jobs |

| 3 | Generate | LLM produces TailorResponse |

| 4 | Render | LLM produces final Markdown CV |

| 5 | Store | System stores CV file in user container |

| 6 | Respond | System returns download/view link |

**Options:**

| Option | Description |

|--------|-------------|

| Per Job | Generate separate CVs for each selected job |

| Group All | Generate a single CV applicable to all selected jobs |

**Output:**

- Markdown-formatted CV document

- Stored in user's Azure Blob Storage container

- Downloadable and viewable via provided link

---

## 11. CORE BUSINESS RULES

### 11.1 Authentication & Access Control

| Rule | Description |

|------|-------------|

| Current | Simple authentication using database-stored credentials |

| Future | Migration to Keycloak for enhanced security |

| Ownership | Users can only access their own data |

| Admin | System administrators have elevated permissions |

### 11.2 Data Storage

| Asset | Storage Location |

|-------|------------------|

| User Files | Azure Blob Storage (user-specific containers) |

| Structured Data | Database |

| LLM Results | Database |

### 11.3 Processing Behavior

| Aspect | Specification |

|--------|---------------|

| File Uploads | One file at a time |

| Profile Extraction | Asynchronous queue processing |

| Merging | Automatic when all files processed |

| Duplicate Jobs | Detected via URL uniqueness |

### 11.4 User Interactions

| Action | Allowed Users |

|--------|---------------|

| Delete Job | Original submitter or Admin |

| Mark Job as Interesting | Any authenticated user |

| Update Profile | Profile owner |

| Delete Report | Report owner |

---

## 12. APPENDICES

### 12.1 Glossary of Terms

| Term | Definition |

|------|------------|

| **LLM** | Large Language Model - AI system for text processing
|

| **Canonical** | Standardized, authoritative version |

| **Container** | Isolated storage location in Azure Blob Storage
|

| **Fragment** | Partial profile data from a single document |

| **Normalization** | Converting raw data into a standard
structured format |

| **Tailored CV** | A CV customized for specific job applications
|

### 12.2 State Transitions

**UserFile States:**

```

Pending → Processing → Processed → Merged

↘ Failed

```

**MatchReport States:**

```

Created → Processing → Completed

↘ Failed

```

### 12.3 Version History

| Version | Date | Changes |

|---------|------|---------|

| 1.0 | Previous | Initial V1 specification |
| 1.1 | Current | Clarified profile processing sessions, deterministic matching scoring and eligibility, LLM responsibilities, match snapshots, profile evidence/precedence, and tailored CV source-of-truth rules |

---

_This specification document is the authoritative source for the Talent
Intelligence Platform's functional requirements and behavior._
