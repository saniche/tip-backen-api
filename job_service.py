from pydantic import BaseModel, ConfigDict

from llm_structured import call_openai_structured


class JobRequirementsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    qualifications: list[str]
    skills: list[str]


class JobNormalizationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key_responsibilities: list[str]
    required: JobRequirementsOutput
    desirable: JobRequirementsOutput
    technical_stack: list[str]


JOB_NORMALIZATION_SYSTEM_PROMPT = (
    "Extract job responsibilities, required and desirable qualifications and skills, and technical stack. "
    "Return only explicit facts from the job posting. Use empty arrays when a category is absent."
)


async def normalize_job_content(content: str) -> dict:
    output = await call_openai_structured(
        JOB_NORMALIZATION_SYSTEM_PROMPT, content, JobNormalizationOutput, operation="job_normalizer"
    )
    return output.model_dump()
