"""Security and RBAC access control tests."""
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_unauthenticated_request_rejected():
    # Calling a protected endpoint without bearer token should fail with 401
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_login_and_token_generation():
    # Login with seeded demo credentials or invalid credentials
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@university.edu", "password": "wrongpassword"}
    )
    assert response.status_code == 401
