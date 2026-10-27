from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict

from shared.llm_structured import call_openai_structured

JobSource = Literal["LinkedIn", "Indeed", "JobBank", "CompanyWebsite", "Other"]


class JobNormalizationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    company: str
    location: str
    salary: str
    source: JobSource
    posting_date: str | None
    key_responsibilities: list[str]
    requirements: list[str]
    desirables: list[str]
    tools_and_technologies: list[str]
    additionals: list[str]


JOB_NORMALIZATION_SYSTEM_PROMPT = (
    "Normalize one job posting into the requested schema. Extract the employer, normalized job title, "
    "location (city, region, province, state, country, or Remote), salary, posting source, posting date, "
    "responsibilities, mandatory qualifications or skills, preferred qualifications or skills, "
    "technologies/tools/frameworks/environment, and other important details such as benefits, clearance, "
    "visa, and work conditions. Use concise strings in "
    "the lists. Include only facts supported by the posting or URL; do not invent details. "
    "For missing text fields use an empty string, for a missing posting date use null, and for missing "
    "list fields use an empty list. Return source as exactly LinkedIn, Indeed, JobBank, CompanyWebsite, "
    "or Other, inferring it from the URL; use Other if it cannot be identified. Use Remote for location "
    "only when the posting identifies the role as remote. Normalize an explicit posting date to ISO 8601. "
    "A clear relative date such as 'posted 3 days ago' may be calculated from the supplied UTC processing "
    "date; otherwise return null for the date. The application will use the day before the processing date "
    "as a fallback. Return only the schema fields: no explanations, commentary, markdown, or additional text."
)


async def normalize_job_content(url: str, content: str) -> dict:
    processing_date = datetime.now(timezone.utc).date()
    user_content = (
        f"URL: {url}\n"
        f"Processing date (UTC): {processing_date.isoformat()}\n"
        f"Job posting content:\n{content}"
    )
    output = await call_openai_structured(
        JOB_NORMALIZATION_SYSTEM_PROMPT, user_content, JobNormalizationOutput, operation="job_normalizer"

    )
    normalized = output.model_dump()
    if normalized["posting_date"] is None:
        normalized["posting_date"] = (processing_date - timedelta(days=1)).isoformat()
    return normalized
