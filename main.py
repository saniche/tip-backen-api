from fastapi import FastAPI

from database import Base, engine
from routers import (
    auth_router,
    cv_tailoring_router,
    download_router,
    job_matching_router,
    job_normalizer,
    processing_jobs_router,
    profile_builder_router,
)

app = FastAPI(title="Job Search Aggregator API")

# Dev convenience only — use Alembic migrations instead of create_all once this runs anywhere real.
Base.metadata.create_all(bind=engine)

app.include_router(auth_router.router)
app.include_router(job_normalizer.router)
app.include_router(profile_builder_router.router)
app.include_router(job_matching_router.router)
app.include_router(cv_tailoring_router.router)
app.include_router(download_router.router)
app.include_router(processing_jobs_router.router)
