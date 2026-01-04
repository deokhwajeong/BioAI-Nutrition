"""Unit tests for BioAI Nutrition API using pytest and TestClient.

This version aligns payload keys with the updated event models.
It tests health, diet, activity, sleep, delete, and unauthorized scenarios.
"""

import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app, settings

client = TestClient(app)
headers = {"X-API-Key": settings.api_key}


def test_health() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_diet_event() -> None:
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


def test_activity_event() -> None:
    payload = {
        "user_id": "test-user",
        "timestamp": "2024-01-01T00:00:00Z",
        # Using descriptive keys consistent with the ActivityEvent model
        "activity_type": "running",
        "duration_minutes": 30.0,
        "calories_burned": 300,
    }
    response = client.post("/events/activity", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == payload


def test_sleep_event() -> None:
    payload = {
        "user_id": "test-user",
        "timestamp": "2024-01-01T00:00:00Z",
        # Sleep quality must be between 1 and 5 per model constraints
        "duration_minutes": 480,
        "sleep_quality": 4,
    }
    response = client.post("/events/sleep", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == payload


def test_user_delete() -> None:
    response = client.delete("/users/test-user", headers=headers)
    assert response.status_code == 204


def test_unauthorized() -> None:
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
