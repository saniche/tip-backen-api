import httpx
from azure.core.exceptions import ServiceRequestError, ServiceResponseError
from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError


def is_transient_failure(error: BaseException) -> bool:
    transient = (
        APIConnectionError,
        APITimeoutError,
        InternalServerError,
        RateLimitError,
        ServiceRequestError,
        ServiceResponseError,
        httpx.NetworkError,
        httpx.TimeoutException,
        ConnectionError,
        TimeoutError,
    )
    seen = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        if isinstance(current, transient):
            return True
        seen.add(id(current))
        current = current.__cause__
    return False
