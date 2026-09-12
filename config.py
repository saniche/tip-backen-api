from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_MODELS = {
	"profile_builder": os.getenv("OPENAI_PROFILE_BUILDER_MODEL", "gpt-4o-mini"),
	"job_normalizer": os.getenv("OPENAI_JOB_NORMALIZER_MODEL", "gpt-4o-mini"),
	"job_matching": os.getenv("OPENAI_JOB_MATCHING_MODEL", "gpt-4o-mini"),
	"cv_tailoring": os.getenv("OPENAI_CV_TAILORING_MODEL", "gpt-4o-mini"),
}
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
