from tests.keycloak_stub import issue_token


def test_health_and_readiness(client):
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_authentication_and_invalid_token(client):
    token = issue_token(client, "a@example.com")["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "a@example.com"
    assert client.get("/api/v1/profile", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_error_shape_for_missing_resource(client, user):
    response = client.get(
        "/api/v1/processing-jobs/missing", headers={"Authorization": f"Bearer {user['access_token']}"}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
