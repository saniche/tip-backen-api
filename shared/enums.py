import enum


class ProfileSessionStatus(str, enum.Enum):
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProfileFileStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ApplicationStatus(str, enum.Enum):
    NOT_STARTED = "NotStarted"
    REGISTERED = "Registered"
    APPLIED = "Applied"
    CONTACTED = "Contacted"
    SCREENING = "Screening"
    INTERVIEW = "Interview"
    ON_HOLD = "OnHold"
    CLOSED = "Closed"
    REJECTED = "Rejected"
    OFFERED = "Offered"
    ACCEPTED = "Accepted"


class ProcessingJobType(str, enum.Enum):
    PROFILE_BUILD = "profile_build"
    JOB_NORMALIZE = "job_normalize"
    MATCHING = "matching"
    CV_TAILOR = "cv_tailor"


class ProcessingJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class JobNormalizationStatus(str, enum.Enum):
    EXISTING = "existing"
    PROCESSING = "processing"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobInterestStatus(str, enum.Enum):
    CREATED = "created"
    EXISTING = "existing"


class MatchReportStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class MatchScoringStatus(str, enum.Enum):
    SCORED = "scored"
    UNSCORABLE = "unscorable"


class MatchJudgment(str, enum.Enum):
    YES = "Yes"
    NO = "No"


class LegacyCvMode(str, enum.Enum):
    PER_JOB = "per_job"
    GROUP_ALL = "group_all"


class TailoringMode(str, enum.Enum):
    PER_JOB = "per_job"
    GENERAL = "general"


class TailoringRequestStatus(str, enum.Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class TailoredDocumentKind(str, enum.Enum):
    CV = "cv"
    COVER_LETTER = "cover_letter"


class TailoredDocumentStatus(str, enum.Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
