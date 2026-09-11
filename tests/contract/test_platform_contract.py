def test_health_and_readiness(client):
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_authentication_and_invalid_token(client):
    response = client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "password123"})
    assert response.status_code == 201
    assert "access_token" in response.json()
    assert client.get("/api/v1/profile", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_error_shape_for_missing_resource(client, user):
    response = client.get(
        "/api/v1/processing-jobs/missing", headers={"Authorization": f"Bearer {user['access_token']}"}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
