from pathlib import Path

from db import models as db_models
from db.base import Base
from main import app


def test_schema_and_entity_packages_remain_separate():
    schema_files = Path("api/schemas").rglob("*.py")
    assert all("sqlalchemy" not in file_path.read_text(encoding="utf-8").lower() for file_path in schema_files)
    entity_files = Path("db/models").rglob("*.py")
    assert all("BaseModel" not in file_path.read_text(encoding="utf-8") for file_path in entity_files)


def test_every_operation_has_a_documented_success_schema():
    schema = app.openapi()
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            assert operation.get("summary"), f"{method.upper()} {path} has no summary"
            assert operation.get("description"), f"{method.upper()} {path} has no description"
            assert operation.get("tags"), f"{method.upper()} {path} has no tags"
            assert operation.get("operationId"), f"{method.upper()} {path} has no operation ID"
            responses = operation["responses"]
            success_responses = [code for code in responses if code.startswith("2")]
            assert success_responses, f"{method.upper()} {path} has no successful response"
            for status_code in success_responses:
                if status_code == "204":
                    continue
                assert any("schema" in media for media in responses[status_code].get("content", {}).values()), (
                    f"{method.upper()} {path} response {status_code} has no schema"
                )


def test_schema_names_do_not_collide_with_database_entities():
    schema_names = set(app.openapi()["components"]["schemas"])
    entity_names = {
        model.__name__
        for model in vars(db_models).values()
        if isinstance(model, type) and model is not Base and issubclass(model, Base)
    }
    assert schema_names.isdisjoint(entity_names)


def test_operation_ids_are_unique_and_protected_routes_use_bearer_auth():
    operations = [
        operation
        for path_item in app.openapi()["paths"].values()
        for method, operation in path_item.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]
    operation_ids = [operation["operationId"] for operation in operations]
    assert len(operation_ids) == len(set(operation_ids))

    schemes = app.openapi()["components"]["securitySchemes"]
    assert schemes["BearerAuth"]["type"] == "http"
    assert schemes["BearerAuth"]["scheme"] == "bearer"
    assert "security" not in app.openapi()["paths"]["/api/v1/auth/login"]["post"]
    assert app.openapi()["paths"]["/api/v1/jobs"]["get"]["security"] == [{"BearerAuth": []}]


def test_file_upload_and_download_contracts_are_documented():
    schema = app.openapi()
    assert (
        "multipart/form-data"
        in schema["paths"]["/api/v1/profile/sessions/{session_id}/files"]["post"]["requestBody"]["content"]
    )
    assert "multipart/form-data" in schema["paths"]["/api/v1/defaults/cv/file"]["post"]["requestBody"]["content"]
    download = schema["paths"]["/api/v1/cv/{tailored_cv_id}/download"]["get"]["responses"]["200"]
    assert download["content"]["text/markdown"]["schema"] == {"type": "string", "format": "binary"}
    assert "X-Temporary-Download-URL" in download["headers"]


def test_docs_and_openapi_routes_return_success(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 200


def test_dashboard_and_application_filters_are_documented():
    schema = app.openapi()
    dashboard = schema["paths"]["/api/v1/dashboard/summary"]["get"]
    assert dashboard["security"] == [{"BearerAuth": []}]
    assert {parameter["name"] for parameter in dashboard["parameters"]} == {"today", "follow_up_limit"}
    assert dashboard["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/DashboardSummaryResponse"
    }
    application_list = schema["paths"]["/api/v1/applications"]["get"]
    assert {"status", "follow_up_from", "follow_up_to"} <= {
        parameter["name"] for parameter in application_list["parameters"]
    }
    assert {"matching_reports", "tailoring_requests"} <= set(
        schema["components"]["schemas"]["DashboardSummaryResponse"]["properties"]
    )


def test_validation_errors_use_the_shared_error_envelope(client):
    response = client.post("/api/v1/auth/register", json={"email": "candidate@example.com"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
