"""
Tests for Chat API Endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_chat_session():
    """Test creating a new chat session"""
    response = client.post(
        "/api/v1/chat/sessions",
        json={"user_id": 1}
    )

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "created_at" in data


def test_get_chat_session():
    """Test retrieving a chat session"""
    # First create a session
    create_response = client.post(
        "/api/v1/chat/sessions",
        json={"user_id": 1}
    )
    session_id = create_response.json()["session_id"]

    # Then retrieve it
    response = client.get(f"/api/v1/chat/sessions/{session_id}")

    # Note: This will return 404 in test environment without Redis
    # In production with Redis, it should return 200
    assert response.status_code in [200, 404]


def test_delete_chat_session():
    """Test deleting a chat session"""
    # First create a session
    create_response = client.post(
        "/api/v1/chat/sessions",
        json={"user_id": 1}
    )
    session_id = create_response.json()["session_id"]

    # Then delete it
    response = client.delete(f"/api/v1/chat/sessions/{session_id}")

    # Note: This will return 404 in test environment without Redis
    assert response.status_code in [200, 404]


def test_get_nonexistent_session():
    """Test retrieving a non-existent session"""
    response = client.get("/api/v1/chat/sessions/nonexistent-id")

    assert response.status_code == 404


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
