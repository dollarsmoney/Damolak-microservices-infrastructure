"""
Data Service Tests
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "damolak-data-service"
    assert "uptime" in data


def test_list_items():
    res = client.get("/items")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "pagination" in data


def test_list_items_pagination():
    res = client.get("/items?page=1&limit=2")
    assert res.status_code == 200
    data = res.json()
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["limit"] == 2


def test_create_item():
    res = client.post("/items", json={
        "title": "Test Item",
        "description": "A test data item",
        "category": "testing",
        "payload": {"key": "value"},
        "priority": "high",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Test Item"
    assert data["priority"] == "high"
    assert "id" in data


def test_create_item_validation():
    res = client.post("/items", json={
        "title": "",
        "payload": {},
    })
    assert res.status_code == 422  # Validation error


def test_get_item():
    # Create first
    create_res = client.post("/items", json={
        "title": "Lookup Test",
        "payload": {"test": True},
    })
    item_id = create_res.json()["id"]

    # Retrieve
    res = client.get(f"/items/{item_id}")
    assert res.status_code == 200
    assert res.json()["id"] == item_id


def test_get_item_not_found():
    res = client.get("/items/nonexistent-id")
    assert res.status_code == 404


def test_update_item():
    create_res = client.post("/items", json={
        "title": "Update Test",
        "payload": {},
    })
    item_id = create_res.json()["id"]

    res = client.put(f"/items/{item_id}", json={"title": "Updated Title"})
    assert res.status_code == 200
    assert res.json()["title"] == "Updated Title"


def test_delete_item():
    create_res = client.post("/items", json={
        "title": "Delete Test",
        "payload": {},
    })
    item_id = create_res.json()["id"]

    res = client.delete(f"/items/{item_id}")
    assert res.status_code == 200

    # Verify deleted
    res = client.get(f"/items/{item_id}")
    assert res.status_code == 404
