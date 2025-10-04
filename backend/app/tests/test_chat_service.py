"""
Tests for Chat Service
"""
import pytest
from app.services.chat_service import ChatService
from app.schemas.chat import MessageRole


@pytest.fixture
def chat_service():
    return ChatService()


def test_build_system_prompt(chat_service):
    """Test system prompt generation"""
    prompt = chat_service._build_system_prompt(portfolio_id=1)

    assert prompt is not None
    assert "financial advisor" in prompt.lower()
    assert "portfolio" in prompt.lower()
    assert "1" in prompt  # Portfolio ID should be included


def test_build_message_context(chat_service):
    """Test message context building"""
    from app.schemas.chat import ChatMessage
    from datetime import datetime

    messages = [
        ChatMessage(role=MessageRole.USER, content="Hello"),
        ChatMessage(role=MessageRole.ASSISTANT, content="Hi there!"),
        ChatMessage(role=MessageRole.USER, content="What's my portfolio value?"),
    ]

    context = chat_service._build_message_context(messages)

    assert len(context) == 3
    assert context[0]["role"] == "user"
    assert context[0]["content"] == "Hello"


def test_format_tools_for_claude(chat_service):
    """Test MCP tools formatting for Claude API"""
    tools = chat_service._format_tools_for_claude()

    assert len(tools) > 0
    assert all("name" in tool for tool in tools)
    assert all("description" in tool for tool in tools)
    assert all("input_schema" in tool for tool in tools)


def test_is_dashboard_tool(chat_service):
    """Test dashboard tool detection"""
    assert chat_service._is_dashboard_tool("run_efficient_frontier") is True
    assert chat_service._is_dashboard_tool("run_monte_carlo") is True
    assert chat_service._is_dashboard_tool("simulate_rebalancing") is True
    assert chat_service._is_dashboard_tool("get_portfolio_summary") is False


def test_format_sse_event(chat_service):
    """Test SSE event formatting"""
    event = chat_service._format_sse_event("test_event", {"key": "value"})

    assert "event: test_event" in event
    assert "data: " in event
    assert '"key": "value"' in event
    assert event.endswith("\n\n")
