"""
ORM models.

Design notes (see conversation for full rationale):
- Job is global/deduplicated by url — NOT scoped by user. Multiple users can match against the
  same posting without re-extracting it.
- UserProfile is append-only (one row per rebuild, not overwritten) so a JobMatching row can point
  at the exact profile version it was scored against, even after the profile changes later.
- ProcessingJob tracks the two slow, backgrounded operations (profile build, CV tailoring) so the
  API can return 202 + a job id immediately and let the client poll for completion.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    role: Mapped[str] = mapped_column(String, default="user")


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


class ProfileSession(Base):
    __tablename__ = "profile_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    status: Mapped[ProfileSessionStatus] = mapped_column(
        Enum(ProfileSessionStatus), default=ProfileSessionStatus.CREATED
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class UserFile(Base):
    __tablename__ = "user_files"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("profile_sessions.id"), index=True)
    filename: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[ProfileFileStatus] = mapped_column(Enum(ProfileFileStatus), default=ProfileFileStatus.PENDING)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ProfileFragment(Base):
    __tablename__ = "profile_fragments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    file_id: Mapped[str] = mapped_column(String, ForeignKey("user_files.id"), index=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_type: Mapped[str] = mapped_column(String, default="extracted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Job(Base):
    """Global, deduplicated by url. Not scoped by user."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    url: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    title: Mapped[str] = mapped_column(String)
    company: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    salary: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    posting_date: Mapped[str | None] = mapped_column(String, nullable=True)
    key_responsibilities: Mapped[list] = mapped_column(JSON, default=list)
    required: Mapped[dict] = mapped_column(JSON, default=dict)  # {"qualifications": [...], "skills": [...]}
    desirable: Mapped[dict] = mapped_column(JSON, default=dict)
    technical_stack: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    submitter_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True, index=True)


class JobInterest(Base):
    __tablename__ = "job_interests"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_job_interest_user_job"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class UserProfile(Base):
    """Append-only: each rebuild creates a new row. The most recent row per user is 'current'."""

    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    data: Mapped[dict] = mapped_column(JSON)  # serialized UserProfile (see profile_builder.UserProfile)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    output_language: Mapped[str] = mapped_column(String, default="English")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MatchReport(Base):
    __tablename__ = "match_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    profile_id: Mapped[str] = mapped_column(String, ForeignKey("user_profiles.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="completed")
    rules_version: Mapped[str] = mapped_column(String, default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class JobMatchingResult(Base):
    __tablename__ = "job_matchings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    report_id: Mapped[str | None] = mapped_column(String, ForeignKey("match_reports.id"), index=True, nullable=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id"), index=True)
    profile_id: Mapped[str] = mapped_column(String, ForeignKey("user_profiles.id"))
    score: Mapped[int] = mapped_column(Float)
    eligible: Mapped[bool] = mapped_column(Boolean)
    scoring_status: Mapped[str] = mapped_column(String)  # "scored" | "unscorable"
    breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    llm_match_output: Mapped[dict] = mapped_column(JSON)  # raw LlmMatchOutput, for audit/debugging
    profile_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    job_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rules_version: Mapped[str] = mapped_column(String, default="v1")
    rank: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TailoredCVRecord(Base):
    __tablename__ = "tailored_cvs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    request_id: Mapped[str | None] = mapped_column(String, ForeignKey("cv_requests.id"), nullable=True, index=True)
    matching_id: Mapped[str] = mapped_column(String, ForeignKey("job_matchings.id"), index=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    blob_path: Mapped[str] = mapped_column(String)  # key/path in Azure Blob Storage
    mode: Mapped[str] = mapped_column(String, default="per_job")
    status: Mapped[str] = mapped_column(String, default="completed")
    target_job_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CVRequest(Base):
    __tablename__ = "cv_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    matching_ids: Mapped[list] = mapped_column(JSON, default=list)
    mode: Mapped[str] = mapped_column(String, default="per_job")
    status: Mapped[str] = mapped_column(String, default="completed")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ProcessingJobType(str, enum.Enum):
    PROFILE_BUILD = "profile_build"
    JOB_NORMALIZE = "job_normalize"
    CV_TAILOR = "cv_tailor"


class ProcessingJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ProcessingJob(Base):
    """Tracks a backgrounded operation so the client can poll GET /jobs/{id} for status/result."""

    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True)
    job_type: Mapped[ProcessingJobType] = mapped_column(Enum(ProcessingJobType))
    status: Mapped[ProcessingJobStatus] = mapped_column(Enum(ProcessingJobStatus), default=ProcessingJobStatus.PENDING)
    result_id: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # points at UserProfile.id or TailoredCVRecord.id
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
