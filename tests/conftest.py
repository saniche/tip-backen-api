import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")

import pytest
from fastapi.testclient import TestClient

import cv_tailoring_router
import job_normalizer
from database import Base, TestingSessionLocal, get_db, get_testing_db, testing_engine
from main import app
import profile_builder_router


@pytest.fixture(autouse=True)
def database():
    profile_builder_router.SessionLocal = TestingSessionLocal
    cv_tailoring_router.SessionLocal = TestingSessionLocal
    job_normalizer.SessionLocal = TestingSessionLocal
    Base.metadata.create_all(testing_engine)
    yield
    Base.metadata.drop_all(testing_engine)


@pytest.fixture
def database_session(database):
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = get_testing_db
    return TestClient(app)


@pytest.fixture
def user(client):
    response = client.post("/api/v1/auth/register", json={"email": "user@example.com", "password": "password123"})
    return response.json()
