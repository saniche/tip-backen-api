from pathlib import Path


def test_migration_chain_is_complete():
    versions = sorted(Path("alembic/versions").glob("*.py"))
    names = [path.name for path in versions]
    assert "001_initial_schema.py" in names
    assert "002_jobs_and_interests.py" in names
    assert "003_matching_reports.py" in names
    assert "004_tailored_cvs.py" in names