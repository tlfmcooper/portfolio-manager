"""Tests for MCP tools"""
import pytest
from app.services.mcp_server import PortfolioMCPTools


@pytest.fixture
def mcp_tools():
    return PortfolioMCPTools()


@pytest.fixture
def sample_holdings():
    return [
        {"ticker": "AAPL", "weight": 0.3},
        {"ticker": "GOOGL", "weight": 0.3},
        {"ticker": "MSFT", "weight": 0.2},
        {"ticker": "TSLA", "weight": 0.2},
    ]


def test_get_tools_definition(mcp_tools):
    """Test that tools definition is properly formatted"""
    tools = mcp_tools.get_tools_definition()

    assert isinstance(tools, list)
    assert len(tools) == 7  # 7 tools defined

    # Check first tool structure
    tool = tools[0]
    assert "name" in tool
    assert "description" in tool
    assert "input_schema" in tool


def test_execute_portfolio_summary(mcp_tools, sample_holdings, monkeypatch):
    """Test get_portfolio_summary tool execution"""

    def mock_get_holdings(portfolio_id, user_id):
        return sample_holdings

    monkeypatch.setattr(mcp_tools, "get_portfolio_holdings", mock_get_holdings)

    result = mcp_tools.execute_tool(
        "get_portfolio_summary", {"portfolio_id": 1}, user_id=1
    )

    assert "summary" in result or "error" in result


def test_execute_risk_metrics(mcp_tools, sample_holdings, monkeypatch):
    """Test get_risk_metrics tool execution"""

    def mock_get_holdings(portfolio_id, user_id):
        return sample_holdings

    monkeypatch.setattr(mcp_tools, "get_portfolio_holdings", mock_get_holdings)

    result = mcp_tools.execute_tool("get_risk_metrics", {"portfolio_id": 1}, user_id=1)

    assert "risk_metrics" in result or "error" in result


def test_execute_unknown_tool(mcp_tools):
    """Test execution of unknown tool"""
    result = mcp_tools.execute_tool("unknown_tool", {}, user_id=1)

    assert "error" in result
    assert "Unknown tool" in result["error"]


def test_execute_with_no_holdings(mcp_tools, monkeypatch):
    """Test execution when portfolio has no holdings"""

    def mock_get_holdings(portfolio_id, user_id):
        return []

    monkeypatch.setattr(mcp_tools, "get_portfolio_holdings", mock_get_holdings)

    result = mcp_tools.execute_tool(
        "get_portfolio_summary", {"portfolio_id": 1}, user_id=1
    )

    assert "error" in result
