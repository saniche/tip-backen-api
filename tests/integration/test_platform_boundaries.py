def test_private_processing_resource_is_owner_scoped(client):
    first = client.post("/api/v1/auth/register", json={"email": "one@example.com", "password": "password123"}).json()
    second = client.post("/api/v1/auth/register", json={"email": "two@example.com", "password": "password123"}).json()
    response = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {second['access_token']}"})
    assert response.status_code == 404
