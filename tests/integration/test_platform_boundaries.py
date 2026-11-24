from tests.keycloak_stub import issue_token


def test_private_processing_resource_is_owner_scoped(client):
    issue_token(client, "one@example.com")
    second = issue_token(client, "two@example.com")
    response = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {second['access_token']}"})
    assert response.status_code == 404
