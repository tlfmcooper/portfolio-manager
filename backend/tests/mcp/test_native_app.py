"""The native app resource is authorized and preserves MCP UI metadata."""

import asyncio
from types import SimpleNamespace

import pytest

from app.mcp.auth import MCPAuthContext
from app.mcp.errors import MCPError
from app.mcp.registry import get_registry


def test_resource_catalog_separates_concrete_resources_from_templates():
    registry = get_registry()
    # MCP resources/list requires a URI on every item. One template-only item
    # makes SDK clients reject the entire catalog, including the native app.
    resources = registry.list_resources()
    assert all(isinstance(resource.uri, str) and resource.uri for resource in resources)
    assert "ui://portfolio/app" in {resource.uri for resource in resources}
    assert "market.quote" not in {resource.name for resource in resources}
    assert "market://quote/{symbol}" in {template.uriTemplate for template in registry.list_resource_templates()}


def test_native_resource_and_open_tool_preserve_wire_metadata():
    registry = get_registry()
    context = SimpleNamespace(auth=MCPAuthContext(is_authenticated=True, permissions={"portfolio:read"}))
    resource = asyncio.run(registry.read_resource("ui://portfolio/app", context)).model_dump(by_alias=True, exclude_none=True)
    content = resource["contents"][0]
    assert content["mimeType"] == "text/html;profile=mcp-app"
    assert content["_meta"]["ui"]["nativeAppUrl"] == "https://portfolio.alikone.dev/dashboard?mcpApp=1"
    assert "access_token" not in content["text"]
    opened = asyncio.run(registry.execute_tool("portfolio_open_app", {}, context)).model_dump(by_alias=True)
    assert opened["_meta"]["ui"]["resourceUri"] == content["uri"]


def test_scenario_tool_is_read_only_and_opens_native_ui():
    registry = get_registry()
    tool = next(tool for tool in registry.list_tools() if tool.name == "analytics_preview_scenario")
    wire = tool.model_dump(by_alias=True, exclude_none=True)
    assert wire["annotations"]["readOnlyHint"] is True
    assert wire["_meta"]["ui"]["resourceUri"] == "ui://portfolio/app"
    with pytest.raises(MCPError):
        asyncio.run(registry.execute_tool(tool.name, {"preset": "msr"}, SimpleNamespace(auth=MCPAuthContext())))


@pytest.mark.parametrize("auth", [MCPAuthContext(), MCPAuthContext(is_authenticated=True, permissions={"market:read"})])
def test_native_resource_requires_authenticated_portfolio_access(auth):
    with pytest.raises(MCPError):
        asyncio.run(get_registry().read_resource("ui://portfolio/app", SimpleNamespace(auth=auth)))
