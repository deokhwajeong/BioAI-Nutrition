import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app, settings

client = TestClient(app)
headers = {"X-API-Key": settings.api_key}

def test_health():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_diet_event():
    payload = {
        "user_id": "test-user",
        "timestamp": "2024-01-01T00:00:00Z",
        "food": "Apple",
        "calories": 95,
        "protein": 0.5,
        "carbs": 25,
        "fat": 0.3,
    }
    response = client.post("/events/diet", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == payload

def test_activity_event():
    payload = {
        "user_id": "test-user",
        "timestamp": "2024-01-01T00:00:00Z",
        "type": "running",
        "duration": 30.0,
        "calories": 300,
    }
    response = client.post("/events/activity", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == payload

def test_sleep_event():
    payload = {
        "user_id": "test-user",
        "timestamp": "2024-01-01T00:00:00Z",
        "duration": 480,
        "quality": 8.5,
    }
    response = client.post("/events/sleep", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == payload

def test_user_delete():
    response = client.delete("/users/test-user", headers=headers)
    assert response.status_code == 204

def test_unauthorized():
    payload = {
        "user_id": "test-user",
        "timestamp": "2024-01-01T00:00:00Z",
        "food": "Apple",
        "calories": 95,
        "protein": 0.5,
        "carbs": 25,
        "fat": 0.3,
    }
    # Missing API key header should return 401
    response = client.post("/events/diet", json=payload)
    assert response.status_code == 401
