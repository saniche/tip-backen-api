import ast
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
    assert "006_profile_session_output_language.py" in names
    assert "007_job_additionals.py" in names
    assert "008_interest_listing_index.py" in names
    migration_path = Path("alembic/versions/007_job_additionals.py")
    migration_tree = ast.parse(migration_path.read_text(encoding="utf-8"))
    revision_assignment = next(
        node
        for node in migration_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "revision"
            for target in node.targets
        )
    )
    assert len(ast.literal_eval(revision_assignment.value)) <= 32


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
            session_columns = {row[1]: row[4] for row in connection.execute("PRAGMA table_info('profile_sessions')")}
            job_columns = {row[1]: row[4] for row in connection.execute("PRAGMA table_info('jobs')")}
        assert "ix_jobs_created_at" in job_indexes
        assert "ix_jobs_submitter_id" in job_indexes
        assert "ix_job_interests_user_job" in interest_indexes
        assert session_columns["output_language"] == "'English'"
        assert job_columns["additionals"] == "'[]'"
    finally:
        try:
            database_path.unlink(missing_ok=True)
        except PermissionError:
            pass


def test_interest_listing_index_migration_upgrades_and_downgrades():
    migration_tree = ast.parse(Path("alembic/versions/008_interest_listing_index.py").read_text(encoding="utf-8"))
    revision = ast.literal_eval(
        next(
            node.value
            for node in migration_tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "revision" for target in node.targets)
        )
    )
    assert len(revision) <= 32
    database_path = Path(tempfile.mktemp(suffix=".db"))
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite+pysqlite:///{database_path}"
    alembic = str(Path(sys.executable).with_name("alembic.exe"))

    def run(*args):
        result = subprocess.run([alembic, *args], check=False, capture_output=True, text=True, env=environment)
        assert result.returncode == 0, result.stderr

    def interest_indexes():
        with sqlite3.connect(database_path) as connection:
            return {row[1] for row in connection.execute("PRAGMA index_list('job_interests')")}

    try:
        run("upgrade", "head")
        assert "ix_job_interests_user_created" in interest_indexes()
        run("downgrade", "-1")
        assert "ix_job_interests_user_created" not in interest_indexes()
        assert "ix_job_interests_user_job" in interest_indexes()
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

    from shared.database import Base
    from shared.models import Job, JobInterest, User

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
