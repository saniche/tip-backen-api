import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def test_migration_chain_is_complete():
    versions = sorted(Path("alembic/versions").glob("*.py"))
    names = [path.name for path in versions]
    assert "001_initial_schema.py" in names
    assert "002_jobs_and_interests.py" in names
    assert "003_matching_reports.py" in names
    assert "004_tailored_cvs.py" in names


def test_migrations_upgrade_and_create_jobs_constraints():
    database_path = Path(tempfile.mktemp(suffix=".db"))
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite+pysqlite:///{database_path}"
    try:
        result = subprocess.run(
            [str(Path(sys.executable).with_name("alembic.exe")), "upgrade", "head"],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        assert result.returncode == 0, result.stderr
        with sqlite3.connect(database_path) as connection:
            job_indexes = {row[1] for row in connection.execute("PRAGMA index_list('jobs')")}
            interest_indexes = {row[1] for row in connection.execute("PRAGMA index_list('job_interests')")}
        assert "ix_jobs_created_at" in job_indexes
        assert "ix_jobs_submitter_id" in job_indexes
        assert "ix_job_interests_user_job" in interest_indexes
    finally:
        try:
            database_path.unlink(missing_ok=True)
        except PermissionError:
            pass


@pytest.mark.skipif(
    not os.getenv("TEST_POSTGRES_URL"), reason="Set TEST_POSTGRES_URL to run PostgreSQL boundary coverage"
)
def test_postgres_boundary_uses_fake_provider_and_storage():
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import sessionmaker

    from database import Base
    from models import Job, JobInterest, User

    class FakeJobProvider:
        def extract(self, content):
            return {"title": "Fake role", "content": content}

    class FakeBlobStore:
        def __init__(self):
            self.values = {}

        def upload(self, path, content):
            self.values[path] = content

    provider = FakeJobProvider()
    storage = FakeBlobStore()
    engine = create_engine(os.environ["TEST_POSTGRES_URL"])
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
        user = User(email="postgres-boundary@example.com", hashed_password="hash")
        session.add(user)
        session.flush()
        extracted = provider.extract("Python")
        job = Job(url="https://jobs.test/postgres", title=extracted["title"], summary=extracted["content"])
        session.add(job)
        session.flush()
        storage.upload("jobs/fake", extracted)
        session.add(JobInterest(user_id=user.id, job_id=job.id))
        session.commit()
        session.add(JobInterest(user_id=user.id, job_id=job.id))
        with pytest.raises(IntegrityError):
            session.commit()
        assert storage.values["jobs/fake"]["title"] == "Fake role"
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
