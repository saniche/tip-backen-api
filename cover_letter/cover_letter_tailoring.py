"""Cover letter tailoring (LLM -> validated JSON; the server renders and stores the file).

Facts that must be exact (sender header, recipient/company, role title, date, signature) are
added by code in the writer. The LLM only writes greeting, body paragraphs and closing, and the
paragraphs are checked so that numbers, proper nouns, technologies and seniority claims exist in
the supplied profile/job context.
"""

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field

from shared.grounding import collect_strings, source_vocabulary, unsupported_facts
from shared.llm_structured import call_openai_structured

MAX_STYLE_REFERENCE_CHARS = 6000
STYLE_TOLERANCE = 0.35  # +/- share of the style reference's length


class CoverLetterGroundingError(ValueError):
    """The generated letter mentions facts that are not in the profile or job."""


@dataclass
class TailoredCoverLetter:
    greeting: str = ""
    paragraphs: list[str] = field(default_factory=list)
    closing: str = ""


class CoverLetterOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    greeting: str = Field(min_length=1)
    paragraphs: list[str] = Field(min_length=1, max_length=6)
    closing: str = Field(min_length=1)


COVER_LETTER_SYSTEM_PROMPT = (
    "Write a tailored cover letter using only the supplied profile and job. "
    "Return a greeting, 3 to 4 body paragraphs and a closing, written in the requested output_language. "
    "Do NOT include the sender's address block, recipient, date or signature: they are added by the system. "
    "Do not invent facts: every employer, technology, credential, number, achievement and job title you "
    "mention must come from the supplied profile or job, and never claim seniority or leadership the profile "
    "does not state. Connect the candidate's real experience to the job's requirements and responsibilities. "
    "Aim for roughly 250 to 350 words in total unless a length is implied by a style reference."
)
STYLE_REFERENCE_ADDENDUM = (
    " A style_reference letter is supplied. Use it ONLY to match tone, voice, formality, paragraph structure "
    "and approximate length. Do not reuse any fact, employer, recipient, date, number or achievement from it; "
    "every fact must come from the profile. Stay close to its register."
)


def _word_count(letter: TailoredCoverLetter) -> int:
    return len(" ".join([letter.greeting, *letter.paragraphs, letter.closing]).split())


def style_deviation(letter: TailoredCoverLetter, reference: str | None) -> str | None:
    """A message when the letter's length strays too far from the style reference, else None."""
    if not reference or not reference.strip():
        return None
    target = len(reference.split())
    if target < 40:  # too short to say anything about the expected length
        return None
    low, high = round(target * (1 - STYLE_TOLERANCE)), round(target * (1 + STYLE_TOLERANCE))
    actual = _word_count(letter)
    if low <= actual <= high:
        return None
    return f"The letter has {actual} words; the style reference suggests between {low} and {high} words"


def validate_letter_grounding(letter: TailoredCoverLetter, profile, job_data) -> None:
    sources = collect_strings(profile) + collect_strings(job_data)
    flagged = unsupported_facts("\n".join(letter.paragraphs), source_vocabulary(sources))
    if flagged:
        details = ", ".join(sorted(flagged)[:5])
        raise CoverLetterGroundingError(f"Cover letter contains unsupported facts: {details}")


async def build_cover_letter(
    profile,
    job_data,
    output_language: str = "English",
    style_reference: str | None = None,
) -> tuple[TailoredCoverLetter, str | None]:
    """Returns the letter and an optional warning (e.g. it still deviates from the style reference)."""
    context = {
        "profile": {k: v for k, v in dict(getattr(profile, "__dict__", {})).items() if k != "AdditionalInformations"},
        "job": getattr(job_data, "__dict__", {}),
        "output_language": output_language,
    }
    system_prompt = COVER_LETTER_SYSTEM_PROMPT
    reference = (style_reference or "").strip()[:MAX_STYLE_REFERENCE_CHARS]
    if reference:
        context["style_reference"] = reference
        system_prompt += STYLE_REFERENCE_ADDENDUM

    feedback: str | None = None
    last_error: CoverLetterGroundingError | None = None
    letter: TailoredCoverLetter | None = None
    deviation: str | None = None
    for _ in range(2):
        attempt = dict(context)
        if feedback:
            attempt["validation_feedback"] = feedback
        output = await call_openai_structured(
            system_prompt, str(attempt), CoverLetterOutput, operation="cover_letter_tailoring"
        )
        candidate = TailoredCoverLetter(**output.model_dump())
        try:
            validate_letter_grounding(candidate, profile, job_data)
        except CoverLetterGroundingError as exc:
            last_error = exc
            feedback = f"Your previous letter was rejected: {exc}. Remove those claims or use only supplied facts."
            continue
        last_error = None
        letter, deviation = candidate, style_deviation(candidate, reference)
        if deviation is None:
            break
        feedback = f"Your previous letter was off-style: {deviation}. Adjust the length accordingly."
    if letter is None:
        raise last_error
    return letter, deviation
