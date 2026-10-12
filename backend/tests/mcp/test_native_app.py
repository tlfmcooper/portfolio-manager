"""The native app resource is authorized and preserves MCP UI metadata."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.mcp.auth import MCPAuthContext
from app.mcp.errors import MCPError
from app.mcp.registry import get_registry
from app.mcp.handlers import native_app_resource


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
    resource = asyncio.run(registry.read_resource("ui://portfolio/app/v2", context)).model_dump(by_alias=True, exclude_none=True)
    content = resource["contents"][0]
    assert content["mimeType"] == "text/html;profile=mcp-app"
    assert content["_meta"]["ui"]["nativeAppUrl"] == "https://portfolio.alikone.dev/api/mcp-app?mcpApp=1"
    assert "domain" not in content["_meta"]["ui"]
    assert content["_meta"]["ui"]["csp"]["frameDomains"] == ["https://portfolio.alikone.dev"]
    assert "event.source === frame.contentWindow && event.origin === nativeOrigin" in content["text"]
    assert "event.source === window.parent" in content["text"]
    assert "window.parent.postMessage(message" in content["text"]
    assert "access_token" not in content["text"]
    opened = asyncio.run(registry.execute_tool("portfolio_open_app", {}, context)).model_dump(by_alias=True)
    assert opened["_meta"]["ui"]["resourceUri"] == content["uri"]
    listed = next(item for item in registry.list_resources() if item.uri == content["uri"])
    assert "domain" not in listed.meta["ui"]
    legacy = asyncio.run(registry.read_resource("ui://portfolio/app", context))
    assert legacy.contents[0].uri == "ui://portfolio/app"
    assert legacy.contents[0].text == content["text"]


def test_every_ui_tool_advertises_a_readable_native_resource():
    registry = get_registry()
    resources = {item.uri for item in registry.list_resources()}
    tools = {item.name: item for item in registry.list_tools()}
    assert tools["analytics_get_monte_carlo"].meta["ui"]["resourceUri"] == "ui://portfolio/app/v2"
    for tool in tools.values():
        if tool.meta.get("ui"):
            assert tool.meta["ui"]["resourceUri"] in resources


def test_analytic_result_preserves_data_and_uses_a_readable_native_resource():
    from app.mcp.handlers import _tool_result

    payload = {"simulation_paths": [], "final_mean": 120, "time_horizon": 252}
    result = _tool_result("Retrieved Monte Carlo analytics.", payload, {"resourceUri": "ui://portfolio/analytics/monte-carlo", "data": payload})
    assert result.structuredContent == payload
    assert result.meta["ui"]["resourceUri"] == "ui://portfolio/app/v2"
    assert json.loads(result.content[1]["text"]) == payload
    context = SimpleNamespace(auth=MCPAuthContext(is_authenticated=True, permissions={"portfolio:read"}))
    assert asyncio.run(get_registry().read_resource(result.meta["ui"]["resourceUri"], context)).contents


def test_scenario_tool_is_read_only_and_opens_native_ui():
    registry = get_registry()
    tool = next(tool for tool in registry.list_tools() if tool.name == "analytics_preview_scenario")
    wire = tool.model_dump(by_alias=True, exclude_none=True)
    assert wire["annotations"]["readOnlyHint"] is True
    assert wire["_meta"]["ui"]["resourceUri"] == "ui://portfolio/app/v2"
    with pytest.raises(MCPError):
        asyncio.run(registry.execute_tool(tool.name, {"preset": "msr"}, SimpleNamespace(auth=MCPAuthContext())))


@pytest.mark.parametrize("uri", ["ui://portfolio/app", "ui://portfolio/app/v2"])
@pytest.mark.parametrize("auth", [MCPAuthContext(), MCPAuthContext(is_authenticated=True, permissions={"market:read"})])
def test_native_resource_requires_authenticated_portfolio_access(auth, uri):
    with pytest.raises(MCPError):
        asyncio.run(get_registry().read_resource(uri, SimpleNamespace(auth=auth)))


def test_native_resource_can_use_a_trusted_https_preview_without_credentials():
    result = native_app_resource("https://private-preview.example.test:8443/api/mcp-app?mcpApp=1").model_dump(by_alias=True)
    ui = result["contents"][0]["_meta"]["ui"]
    assert ui["csp"]["frameDomains"] == ["https://private-preview.example.test:8443"]
    assert "domain" not in ui
    assert ui["nativeAppUrl"] in result["contents"][0]["text"]
    with pytest.raises(ValueError):
        native_app_resource("http://localhost:8868/api/mcp-app?mcpApp=1")
