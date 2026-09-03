from fastapi.testclient import TestClient


def test_auth_login_me_logout(client: TestClient) -> None:
    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "demo@example.com"

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204


def test_auth_login_rejects_bad_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"email": "demo@example.com", "password": "wrong"}
    )
    assert response.status_code == 401
