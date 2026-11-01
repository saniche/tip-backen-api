from api.schemas.requests.applications import ApplicationCreate, ApplicationFieldsUpdate, ApplicationStatusUpdate
from api.schemas.requests.auth import UserCreate, UserLogin
from api.schemas.requests.documents import DefaultDocumentIn
from api.schemas.requests.jobs import JobNormalizeRequest
from api.schemas.requests.matching import JobMatchingRequest, MatchCreateRequest, MatchReportRequest
from api.schemas.requests.profiles import ProfilePatch, ProfileSessionCreate, ProfileUpdate
from api.schemas.requests.tailoring import (
    CoverLetterOptions,
    CvTailoringRequest,
    TailoringRequestIn,
)

__all__ = [
    "ApplicationCreate",
    "ApplicationFieldsUpdate",
    "ApplicationStatusUpdate",
    "CoverLetterOptions",
    "CvTailoringRequest",
    "DefaultDocumentIn",
    "JobMatchingRequest",
    "JobNormalizeRequest",
    "MatchCreateRequest",
    "MatchReportRequest",
    "ProfilePatch",
    "ProfileSessionCreate",
    "ProfileUpdate",
    "TailoringRequestIn",
    "UserCreate",
    "UserLogin",
]
