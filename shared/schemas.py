from api.schemas.common.enums import TailoringMode
from api.schemas.common.errors import ApiErrorResponse, ErrorDetails
from api.schemas.common.pagination import PaginatedResponse
from api.schemas.common.value_objects import RecruiterInfo
from api.schemas.requests.applications import ApplicationCreate, ApplicationFieldsUpdate, ApplicationStatusUpdate
from api.schemas.requests.auth import UserCreate, UserLogin
from api.schemas.requests.jobs import JobNormalizeRequest
from api.schemas.requests.matching import JobMatchingRequest, MatchReportRequest
from api.schemas.requests.profiles import ProfilePatch
from api.schemas.requests.tailoring import CoverLetterOptions, CvTailoringRequest, TailoringRequestIn
from api.schemas.responses.applications import (
    ApplicationJobHeaderResponse as ApplicationJobHeader,
)
from api.schemas.responses.applications import (
    ApplicationJournalPage,
)
from api.schemas.responses.applications import (
    ApplicationJournalResponse as ApplicationJournalItem,
)
from api.schemas.responses.applications import (
    ApplicationStatusHistoryResponse as ApplicationStatusHistoryOut,
)
from api.schemas.responses.auth import AuthTokenResponse as Token
from api.schemas.responses.documents import DefaultDocumentResponse
from api.schemas.responses.jobs import (
    InterestItem,
    InterestJobHeader,
    InterestsPage,
    JobDetailResponse,
    JobInterestResponse,
    JobSummaryResponse,
    NormalizedJobHeader,
    NormalizedJobsResponse,
)
from api.schemas.responses.jobs import (
    JobNormalizationResponse as JobNormalizeOut,
)
from api.schemas.responses.matching import (
    JobMatchingResponse as JobMatchingOut,
)
from api.schemas.responses.matching import (
    MatchReportResponse as MatchReportOut,
)
from api.schemas.responses.matching import (
    MatchResultResponse as MatchResultOut,
)
from api.schemas.responses.processing import ProcessingJobResponse as ProcessingJobOut
from api.schemas.responses.profiles import (
    CurrentProfileResponse,
    ProfileFileUploadResponse,
    ProfileSessionDetailResponse,
    ProfileSessionResponse,
    UserProfileDetailResponse,
    UserProfileSummaryResponse,
)
from api.schemas.responses.tailoring import (
    CvMetadataResponse as CvMetadataOut,
)
from api.schemas.responses.tailoring import (
    CvTailoringResponse as CvTailoringOut,
)
from api.schemas.responses.tailoring import (
    TailoredDocumentResponse,
    TailoringRequestDetailResponse,
    TailoringRequestSummaryResponse,
)
from jobs.normalization_schemas import JobExtraction, JobListing, JobRequirements

__all__ = [
    "ApiErrorResponse",
    "ApplicationCreate",
    "ApplicationFieldsUpdate",
    "ApplicationJobHeader",
    "ApplicationJournalItem",
    "ApplicationJournalPage",
    "ApplicationStatusHistoryOut",
    "ApplicationStatusUpdate",
    "CoverLetterOptions",
    "CurrentProfileResponse",
    "CvMetadataOut",
    "CvTailoringOut",
    "CvTailoringRequest",
    "DefaultDocumentResponse",
    "ErrorDetails",
    "InterestItem",
    "InterestJobHeader",
    "InterestsPage",
    "JobDetailResponse",
    "JobExtraction",
    "JobInterestResponse",
    "JobListing",
    "JobMatchingOut",
    "JobMatchingRequest",
    "JobNormalizeOut",
    "JobNormalizeRequest",
    "JobRequirements",
    "JobSummaryResponse",
    "MatchReportOut",
    "MatchReportRequest",
    "MatchResultOut",
    "NormalizedJobHeader",
    "NormalizedJobsResponse",
    "PaginatedResponse",
    "ProcessingJobOut",
    "ProfileFileUploadResponse",
    "ProfilePatch",
    "ProfileSessionDetailResponse",
    "ProfileSessionResponse",
    "RecruiterInfo",
    "TailoredDocumentResponse",
    "TailoringMode",
    "TailoringRequestDetailResponse",
    "TailoringRequestIn",
    "TailoringRequestSummaryResponse",
    "Token",
    "UserCreate",
    "UserLogin",
    "UserProfileDetailResponse",
    "UserProfileSummaryResponse",
]
