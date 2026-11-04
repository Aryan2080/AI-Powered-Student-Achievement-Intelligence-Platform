"""Integration tests for FastAPI endpoints."""
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert "version" in data


def test_list_opportunities_endpoint():
    response = client.get("/api/v1/opportunities?limit=5")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) > 0
    first = items[0]
    assert "opportunity_id" in first
    assert "title" in first


def test_get_recommendations_endpoint():
    response = client.get("/api/v1/recommendations/STU-2026-0001?top_k=3")
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) <= 3
    if data["recommendations"]:
        first = data["recommendations"][0]
        assert "match_score" in first
        assert "explanation" in first
