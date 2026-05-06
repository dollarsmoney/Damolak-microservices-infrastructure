"""
Notification Service Tests
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "damolak-notification-service"


def test_notify(client):
    res = client.post("/notify", json={
        "event": "item_created",
        "item_id": "test-123",
        "title": "Test Item",
        "channel": "log",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "success"
    assert "notification_id" in data


def test_notify_missing_body(client):
    res = client.post("/notify", data="not json", content_type="text/plain")
    assert res.status_code == 400


def test_bulk_notify(client):
    res = client.post("/notify/bulk", json={
        "notifications": [
            {"event": "item_created", "item_id": "1", "title": "Item 1"},
            {"event": "item_updated", "item_id": "2", "title": "Item 2"},
        ]
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["processed"] == 2


def test_list_notifications(client):
    # Send a notification first
    client.post("/notify", json={
        "event": "test_event",
        "item_id": "test-456",
        "title": "List Test",
    })

    res = client.get("/notifications")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "data" in data
    assert "pagination" in data


def test_stats(client):
    res = client.get("/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert "total_received" in data["data"]


def test_404(client):
    res = client.get("/nonexistent")
    assert res.status_code == 404
