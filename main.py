import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from database import Base, engine
from errors import AppException, translate_exception
import auth_router
import job_matching_router
import job_normalizer
import profile_builder_router
import processing_jobs_router

app = FastAPI(title="Job Search Aggregator API")

logger = logging.getLogger("tip-api")

# Dev convenience only — use Alembic migrations instead of create_all once this runs anywhere real.
Base.metadata.create_all(bind=engine)

@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(AppException)
async def app_error(request: Request, exc: AppException):
    request_id = request.headers.get("X-Request-ID")
    logger.warning("Application error: %s", exc.message, extra={"request_id": request_id, "code": exc.code})
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details, "request_id": request_id}},
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    request_id = request.headers.get("X-Request-ID")
    logger.exception("Unhandled request failure", extra={"request_id": request_id})
    translated = translate_exception(exc)
    return JSONResponse(
        status_code=translated.status_code,
        content={"error": {"code": translated.code, "message": translated.message, "details": translated.details, "request_id": request_id}},
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    code_by_status = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "RESOURCE_NOT_FOUND", 409: "CONFLICT", 422: "VALIDATION_ERROR"}
    request_id = request.headers.get("X-Request-ID")
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={"error": {"code": code_by_status.get(exc.status_code, "VALIDATION_ERROR"), "message": str(exc.detail), "details": None, "request_id": request_id}},
    )


@app.get("/health")
def health():
    # Health check endpoint to verify the service is running.
    return {"status": "ok"}


@app.get("/ready")
def ready():
    # Readiness check endpoint to verify the service is ready to handle requests.
    # Check if database and other dependencies are ready and accessible.
    # Example check: ensure the database engine can connect.
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}


app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(job_normalizer.router, prefix="/api/v1")
app.include_router(job_matching_router.router, prefix="/api/v1")
app.include_router(profile_builder_router.router, prefix="/api/v1")
app.include_router(processing_jobs_router.router, prefix="/api/v1")
