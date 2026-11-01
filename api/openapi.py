import re

from fastapi.routing import APIRoute

from api.schemas.common.errors import ErrorResponse

ERROR_DESCRIPTIONS = {
    400: "The request is invalid or cannot be processed.",
    401: "Authentication is required or the bearer token is invalid.",
    403: "The authenticated user is not permitted to perform this operation.",
    404: "The requested resource was not found.",
    409: "The request conflicts with the current resource state.",
    422: "The request body, query parameters, or uploaded file are invalid.",
    500: "The service could not complete the request.",
    502: "An upstream processing service is unavailable.",
    503: "A required service is not ready.",
}


def error_responses(*status_codes: int) -> dict[int, dict[str, object]]:
    return {code: {"model": ErrorResponse, "description": ERROR_DESCRIPTIONS[code]} for code in status_codes}


def generate_operation_id(route: APIRoute) -> str:
    method = "_".join(sorted(value.lower() for value in (route.methods or set())))
    tag = route.tags[0] if route.tags else "api"
    path = re.sub(r"\{([^}]+)\}", r"by_\1", route.path).strip("/")
    identifier = "_".join((tag, method, route.name, path))
    return re.sub(r"[^a-zA-Z0-9_]+", "_", identifier).strip("_").lower()


def openapi_contract_errors(schema: dict[str, object]) -> list[str]:
    errors = []
    paths = schema.get("paths", {})
    if not isinstance(paths, dict):
        return ["OpenAPI document must contain a paths object."]

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            errors.append(f"{path}: path item must be an object.")
            continue
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                continue
            if not isinstance(operation, dict):
                errors.append(f"{method.upper()} {path}: operation must be an object.")
                continue
            if not operation.get("operationId"):
                errors.append(f"{method.upper()} {path}: missing operationId.")
            responses = operation.get("responses", {})
            successful = [(status, response) for status, response in responses.items() if str(status).startswith("2")]
            if not successful:
                errors.append(f"{method.upper()} {path}: missing successful response.")
            for status, response in successful:
                if str(status) == "204":
                    continue
                content = response.get("content", {}) if isinstance(response, dict) else {}
                if not any(isinstance(media, dict) and "schema" in media for media in content.values()):
                    errors.append(f"{method.upper()} {path}: response {status} has no response schema.")
    return errors
