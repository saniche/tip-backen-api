def test_request_id_and_safe_error_contract(client):
    response = client.get("/api/v1/profile", headers={"X-Request-ID": "obs-123"})
    assert response.status_code == 401
    assert response.headers["x-request-id"] == "obs-123"
    body = response.json()
    assert body["error"]["request_id"] == "obs-123"
    assert "password" not in str(body).lower()


def test_secret_error_is_redacted():
    from errors import safe_message

    assert "secret" not in safe_message("provider failed with API key secret-value").lower()
