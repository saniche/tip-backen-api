import ast
import os
import shutil
import sqlite3
import subprocess
import sysconfig
import tempfile
from pathlib import Path

import pytest


def _alembic_command():
    executable = shutil.which("alembic")
    if executable:
        return [executable]

    script_directories = [Path(sysconfig.get_path("scripts"))]
    if os.name == "nt":
        script_directories.append(Path(sysconfig.get_path("scripts", scheme="nt_user")))
    executable_name = "alembic.exe" if os.name == "nt" else "alembic"
    for directory in script_directories:
        candidate = directory / executable_name
        if candidate.is_file():
            return [str(candidate)]
    raise FileNotFoundError("Alembic command-line script is not installed")


def _run_alembic(environment, *args):
    return subprocess.run(
        [*_alembic_command(), *args],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


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
    assert "009_application_journal.py" in names
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
        result = _run_alembic(environment, "upgrade", "head")
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

    def run(*args):
        result = _run_alembic(environment, *args)
        assert result.returncode == 0, result.stderr

    def interest_indexes():
        with sqlite3.connect(database_path) as connection:
            return {row[1] for row in connection.execute("PRAGMA index_list('job_interests')")}

    try:
        run("upgrade", "head")
        assert "ix_job_interests_user_created" in interest_indexes()
        run("downgrade", "007_job_additionals")
        assert "ix_job_interests_user_created" not in interest_indexes()
        assert "ix_job_interests_user_job" in interest_indexes()
    finally:
        try:
            database_path.unlink(missing_ok=True)
        except PermissionError:
            pass


def test_application_journal_migration_preserves_existing_data_and_reverses():
    database_path = Path(tempfile.mktemp(suffix=".db"))
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite+pysqlite:///{database_path}"

    def run(*args):
        result = _run_alembic(environment, *args)
        assert result.returncode == 0, result.stderr

    try:
        run("upgrade", "008_interest_listing_index")
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "INSERT INTO users (id, email, hashed_password) VALUES (?, ?, ?)",
                ("existing-user", "migration@example.com", "hash"),
            )
            connection.execute(
                "INSERT INTO jobs (id, title, status) VALUES (?, ?, ?)",
                ("existing-job", "Existing job", "completed"),
            )
            connection.execute(
                "INSERT INTO job_interests (id, user_id, job_id) VALUES (?, ?, ?)",
                ("existing-interest", "existing-user", "existing-job"),
            )
            connection.commit()

        run("upgrade", "head")
        with sqlite3.connect(database_path) as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            application_indexes = {
                row[1] for row in connection.execute("PRAGMA index_list('application_journals')")
            }
            history_indexes = {
                row[1] for row in connection.execute("PRAGMA index_list('application_status_history')")
            }
            unique_indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list('application_journals')")
                if row[2] == 1
            }
            unique_index_columns = {
                tuple(
                    column[2]
                    for column in connection.execute(f'PRAGMA index_info("{index_name}")')
                )
                for index_name in unique_indexes
            }
            existing_interest = connection.execute(
                "SELECT id FROM job_interests WHERE id = ?", ("existing-interest",)
            ).fetchone()
        assert {"application_journals", "application_status_history"} <= tables
        assert "ix_application_journals_user_created" in application_indexes
        assert "ix_application_status_history_entry_date" in history_indexes
        assert ("user_id", "job_id") in unique_index_columns
        assert existing_interest == ("existing-interest",)
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "INSERT INTO application_journals (id, user_id, job_id) VALUES (?, ?, ?)",
                ("application-one", "existing-user", "existing-job"),
            )
            connection.commit()
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO application_journals (id, user_id, job_id) VALUES (?, ?, ?)",
                    ("application-two", "existing-user", "existing-job"),
                )

        run("downgrade", "008_interest_listing_index")
        with sqlite3.connect(database_path) as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            existing_job = connection.execute("SELECT id FROM jobs WHERE id = ?", ("existing-job",)).fetchone()
            existing_interest = connection.execute(
                "SELECT id FROM job_interests WHERE id = ?", ("existing-interest",)
            ).fetchone()
        assert "application_journals" not in tables
        assert "application_status_history" not in tables
        assert existing_job == ("existing-job",)
        assert existing_interest == ("existing-interest",)
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
