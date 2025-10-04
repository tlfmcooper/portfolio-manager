"""Tests for chat service"""
import pytest
from app.services.chat_service import ChatService


@pytest.fixture
def chat_service():
    return ChatService()


def test_create_session(chat_service):
    """Test creating a new chat session"""
    session = chat_service.create_session(user_id=1, portfolio_id=1)

    assert "session_id" in session
    assert session["user_id"] == 1
    assert session["portfolio_id"] == 1
    assert "messages" in session
    assert len(session["messages"]) == 0


def test_get_session(chat_service):
    """Test retrieving a chat session"""
    # Create session first
    created = chat_service.create_session(user_id=1)
    session_id = created["session_id"]

    # Retrieve it
    session = chat_service.get_session(user_id=1, session_id=session_id)

    assert session["session_id"] == session_id
    assert session["user_id"] == 1


def test_get_nonexistent_session(chat_service):
    """Test retrieving non-existent session"""
    with pytest.raises(ValueError):
        chat_service.get_session(user_id=1, session_id="nonexistent")


def test_add_message(chat_service):
    """Test adding a message to session"""
    session = chat_service.create_session(user_id=1)
    session_id = session["session_id"]

    chat_service.add_message(user_id=1, session_id=session_id, role="user", content="Hello")

    updated_session = chat_service.get_session(user_id=1, session_id=session_id)

    assert len(updated_session["messages"]) == 1
    assert updated_session["messages"][0]["role"] == "user"
    assert updated_session["messages"][0]["content"] == "Hello"


def test_delete_session(chat_service):
    """Test deleting a session"""
    session = chat_service.create_session(user_id=1)
    session_id = session["session_id"]

    result = chat_service.delete_session(user_id=1, session_id=session_id)

    assert result is True

    with pytest.raises(ValueError):
        chat_service.get_session(user_id=1, session_id=session_id)
