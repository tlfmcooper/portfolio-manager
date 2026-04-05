"""Regression tests for per-user MCP API keys and MCP auth."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.crud.mcp_api_key import touch_mcp_api_key_last_used
from app.models import MCPAPIKey
from app.mcp.router import _iter_session_sse
from app.mcp.session_store import session_store
from main import create_application


@pytest_asyncio.fixture
async def test_client(tmp_path):
    database_path = tmp_path / "mcp-test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}", future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_application()

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_user_managed_mcp_api_key_flow(test_client: httpx.AsyncClient) -> None:
    initialize_response = await test_client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 100,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"roots": {"listChanged": True}},
                "clientInfo": {"name": "pytest", "version": "1.0.0"},
            },
        },
    )
    assert initialize_response.status_code == 200
    initialize_payload = initialize_response.json()["result"]
    session_id = initialize_response.headers["Mcp-Session-Id"]
    assert initialize_payload["protocolVersion"] == "2025-03-26"
    assert "completions" in initialize_payload["capabilities"]
    assert "logging" in initialize_payload["capabilities"]
    assert initialize_payload["capabilities"]["resources"]["subscribe"] is True

    ping_response = await test_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 101, "method": "ping"},
    )
    assert ping_response.status_code == 200
    assert ping_response.json()["result"] == {}

    initialized_response = await test_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    assert initialized_response.status_code == 202

    logging_response = await test_client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 102,
            "method": "logging/setLevel",
            "params": {"level": "info"},
        },
    )
    assert logging_response.status_code == 200
    assert logging_response.json()["result"] == {}

    register_response = await test_client.post(
        "/api/v1/auth/register",
        json={
            "username": "mcp_tester",
            "email": "mcp_tester@example.com",
            "password": "ValidPass123",
            "full_name": "MCP Tester",
        },
    )
    assert register_response.status_code == 200

    login_response = await test_client.post(
        "/api/v1/auth/login",
        data={"username": "mcp_tester", "password": "ValidPass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    create_key_response = await test_client.post(
        "/api/v1/users/me/mcp-api-keys",
        json={"name": "Integration Key", "expires_in_days": 30},
        headers=auth_headers,
    )
    assert create_key_response.status_code == 201

    key_payload = create_key_response.json()
    raw_key = key_payload["api_key"]
    key_id = key_payload["key"]["id"]
    assert raw_key.startswith("pmcp_")
    assert key_payload["key"]["key_preview"].startswith(key_payload["key"]["key_prefix"])
    assert key_payload["key"]["last_used_at"] is None

    onboarding_status_before_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 119,
            "method": "tools/call",
            "params": {"name": "onboarding_get_status", "arguments": {}},
        },
    )
    assert onboarding_status_before_response.status_code == 200
    assert onboarding_status_before_response.json()["result"]["structuredContent"]["is_onboarded"] is False

    onboarding_form_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 1191,
            "method": "tools/call",
            "params": {"name": "onboarding_open_manual_form", "arguments": {}},
        },
    )
    assert onboarding_form_response.status_code == 200
    assert onboarding_form_response.json()["result"]["structuredContent"]["form"]["submitTool"] == "onboarding_import_assets"

    onboarding_csv_form_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 1192,
            "method": "tools/call",
            "params": {"name": "onboarding_open_csv_import_form", "arguments": {}},
        },
    )
    assert onboarding_csv_form_response.status_code == 200
    assert onboarding_csv_form_response.json()["result"]["structuredContent"]["form"]["submitTool"] == "onboarding_import_csv"

    list_keys_response = await test_client.get("/api/v1/users/me/mcp-api-keys", headers=auth_headers)
    assert list_keys_response.status_code == 200
    listed_keys = list_keys_response.json()
    assert len(listed_keys) == 1
    assert listed_keys[0]["id"] == key_id
    assert listed_keys[0]["name"] == "Integration Key"

    create_holding_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 120,
            "method": "tools/call",
            "params": {
                "name": "holdings_create",
                "arguments": {"ticker": "AAPL", "quantity": 10, "average_cost": 100},
            },
        },
    )
    assert create_holding_response.status_code == 200
    created_holding = create_holding_response.json()["result"]["structuredContent"]
    assert created_holding["ticker"] == "AAPL"

    update_holding_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 121,
            "method": "tools/call",
            "params": {
                "name": "holdings_update",
                "arguments": {"holding_id": created_holding["id"], "quantity": 12, "average_cost": 105},
            },
        },
    )
    assert update_holding_response.status_code == 200
    assert update_holding_response.json()["result"]["structuredContent"]["quantity"] == 12

    cash_deposit_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 122,
            "method": "tools/call",
            "params": {
                "name": "cash_deposit",
                "arguments": {"amount": 500, "currency": "USD", "notes": "Initial funding"},
            },
        },
    )
    assert cash_deposit_response.status_code == 200
    assert cash_deposit_response.json()["result"]["structuredContent"]["new_balance"] == 500

    cash_balance_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 123,
            "method": "tools/call",
            "params": {"name": "portfolio_get_cash_balance", "arguments": {"currency": "USD"}},
        },
    )
    assert cash_balance_response.status_code == 200
    assert cash_balance_response.json()["result"]["structuredContent"]["cash_balance"] == 500

    overview_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 1231,
            "method": "tools/call",
            "params": {"name": "overview_get_dashboard", "arguments": {"currency": "USD"}},
        },
    )
    assert overview_response.status_code == 200
    assert "dashboard" in overview_response.json()["result"]["structuredContent"]

    transactions_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 124,
            "method": "tools/call",
            "params": {"name": "transactions_list", "arguments": {"skip": 0, "limit": 10}},
        },
    )
    assert transactions_response.status_code == 200
    transaction_items = transactions_response.json()["result"]["structuredContent"]["items"]
    assert any(item["transaction_type"] == "DEPOSIT" for item in transaction_items)

    sell_form_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 125,
            "method": "tools/call",
            "params": {"name": "holdings_open_sell_form", "arguments": {"ticker": "AAPL"}},
        },
    )
    assert sell_form_response.status_code == 200
    assert sell_form_response.json()["result"]["structuredContent"]["form"]["submitTool"] == "holdings_sell"

    sell_holding_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 126,
            "method": "tools/call",
            "params": {
                "name": "holdings_sell",
                "arguments": {"ticker": "AAPL", "quantity": 2, "price": 120},
            },
        },
    )
    assert sell_holding_response.status_code == 200
    assert sell_holding_response.json()["result"]["structuredContent"]["quantity_sold"] == 2

    onboarding_status_after_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 1261,
            "method": "resources/read",
            "params": {"uri": "portfolio://current/onboarding-status"},
        },
    )
    assert onboarding_status_after_response.status_code == 200
    assert '"is_onboarded": true' in onboarding_status_after_response.json()["result"]["contents"][0]["text"].lower()

    completion_response = await test_client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 103,
            "method": "completion/complete",
            "params": {
                "ref": {"type": "ref/prompt", "name": "portfolio.analysis.summary"},
                "argument": {"name": "currency", "value": "u"},
            },
        },
    )
    assert completion_response.status_code == 200
    completion_values = completion_response.json()["result"]["completion"]["values"]
    assert "USD" in completion_values

    question_completion_response = await test_client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 104,
            "method": "completion/complete",
            "params": {
                "ref": {"type": "ref/prompt", "name": "portfolio.analysis.summary"},
                "argument": {"name": "question", "value": "ris"},
            },
        },
    )
    assert question_completion_response.status_code == 200
    question_values = question_completion_response.json()["result"]["completion"]["values"]
    assert any("risk" in value.lower() for value in question_values)

    resource_templates_response = await test_client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 105, "method": "resources/templates/list", "params": {}},
    )
    assert resource_templates_response.status_code == 200
    resource_templates = resource_templates_response.json()["result"]["resourceTemplates"]
    assert any(item["uriTemplate"] == "market://quote/{symbol}" for item in resource_templates)

    mcp_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "portfolio_get_summary",
                "arguments": {"currency": "USD"},
            },
        },
    )
    assert mcp_response.status_code == 200
    mcp_payload = mcp_response.json()
    assert "error" not in mcp_payload
    assert mcp_payload["result"]["structuredContent"]["name"] == "My Portfolio"
    assert mcp_payload["result"]["structuredContent"]["currency"] == "USD"

    subscribe_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 106,
            "method": "resources/subscribe",
            "params": {"uri": "portfolio://current/summary"},
        },
    )
    assert subscribe_response.status_code == 200
    assert subscribe_response.json()["result"] == {}

    legacy_alias_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 109,
            "method": "tools/call",
            "params": {
                "name": "portfolio.get_summary",
                "arguments": {"currency": "USD"},
            },
        },
    )
    assert legacy_alias_response.status_code == 200
    assert legacy_alias_response.json()["result"]["structuredContent"]["currency"] == "USD"

    unsubscribe_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 107,
            "method": "resources/unsubscribe",
            "params": {"uri": "portfolio://current/summary"},
        },
    )
    assert unsubscribe_response.status_code == 200
    assert unsubscribe_response.json()["result"] == {}

    refreshed_keys_response = await test_client.get("/api/v1/users/me/mcp-api-keys", headers=auth_headers)
    assert refreshed_keys_response.status_code == 200
    refreshed_key = refreshed_keys_response.json()[0]
    assert refreshed_key["last_used_at"] is not None

    settings_list_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 127,
            "method": "tools/call",
            "params": {"name": "settings_list_mcp_api_keys", "arguments": {}},
        },
    )
    assert settings_list_response.status_code == 200
    settings_items = settings_list_response.json()["result"]["structuredContent"]["items"]
    assert any(item["id"] == key_id for item in settings_items)

    settings_form_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 128,
            "method": "tools/call",
            "params": {"name": "settings_open_create_mcp_api_key_form", "arguments": {}},
        },
    )
    assert settings_form_response.status_code == 200
    assert settings_form_response.json()["result"]["structuredContent"]["form"]["submitTool"] == "settings_create_mcp_api_key"

    create_settings_key_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 129,
            "method": "tools/call",
            "params": {
                "name": "settings_create_mcp_api_key",
                "arguments": {"name": "Secondary Key", "expires_in_days": 90},
            },
        },
    )
    assert create_settings_key_response.status_code == 200
    created_settings_key = create_settings_key_response.json()["result"]["structuredContent"]["key"]
    secondary_key_id = created_settings_key["id"]
    assert create_settings_key_response.json()["result"]["structuredContent"]["api_key"].startswith("pmcp_")

    rotate_settings_key_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 130,
            "method": "tools/call",
            "params": {
                "name": "settings_rotate_mcp_api_key",
                "arguments": {"key_id": secondary_key_id, "name": "Secondary Key Rotated", "expires_in_days": 120},
            },
        },
    )
    assert rotate_settings_key_response.status_code == 200
    assert rotate_settings_key_response.json()["result"]["structuredContent"]["key"]["name"] == "Secondary Key Rotated"

    settings_resource_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 131,
            "method": "resources/read",
            "params": {"uri": "settings://mcp-api-keys"},
        },
    )
    assert settings_resource_response.status_code == 200
    settings_resource_text = settings_resource_response.json()["result"]["contents"][0]["text"]
    assert "Secondary Key Rotated" in settings_resource_text

    revoke_settings_key_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 132,
            "method": "tools/call",
            "params": {"name": "settings_revoke_mcp_api_key", "arguments": {"key_id": secondary_key_id}},
        },
    )
    assert revoke_settings_key_response.status_code == 200
    assert revoke_settings_key_response.json()["result"]["structuredContent"]["message"] == "MCP API key revoked"

    revoke_response = await test_client.delete(f"/api/v1/users/me/mcp-api-keys/{key_id}", headers=auth_headers)
    assert revoke_response.status_code == 200

    revoked_mcp_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "portfolio_get_summary",
                "arguments": {"currency": "USD"},
            },
        },
    )
    assert revoked_mcp_response.status_code == 200
    revoked_payload = revoked_mcp_response.json()
    assert revoked_payload["error"]["code"] == -32001

    delete_session_response = await test_client.delete("/mcp", headers={"Mcp-Session-Id": session_id})
    assert delete_session_response.status_code == 204

    missing_session_response = await test_client.post(
        "/mcp",
        headers={"x-mcp-api-key": raw_key, "Mcp-Session-Id": session_id},
        json={"jsonrpc": "2.0", "id": 108, "method": "ping"},
    )
    assert missing_session_response.status_code == 404


@pytest.mark.asyncio
async def test_touch_mcp_api_key_last_used_handles_timezone_aware_datetimes() -> None:
    class DummySession:
        def __init__(self) -> None:
            self.commit_count = 0

        async def commit(self) -> None:
            self.commit_count += 1

    api_key = MCPAPIKey(
        user_id=1,
        name="Primary",
        key_prefix="pmcp_deadbeef",
        key_hash="hash",
        permissions_json='["portfolio:read"]',
        last_used_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    session = DummySession()

    await touch_mcp_api_key_last_used(session, api_key)

    assert session.commit_count == 1
    assert api_key.last_used_at is not None
    assert api_key.last_used_at.tzinfo is not None


@pytest.mark.asyncio
async def test_mcp_session_stream_emits_keepalive_when_idle(test_client: httpx.AsyncClient) -> None:
    session = await session_store.create_session()
    event_iter = _iter_session_sse(session.session_id)
    first_line = await asyncio.wait_for(anext(event_iter), timeout=1)
    second_line = await asyncio.wait_for(anext(event_iter), timeout=12)
    await event_iter.aclose()

    assert first_line.startswith(": stream-open")
    assert second_line.strip() == ": keepalive"


@pytest.mark.asyncio
async def test_initialize_rejects_batched_initialize(test_client: httpx.AsyncClient) -> None:
    response = await test_client.post(
        "/mcp",
        json=[
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "pytest"}},
            }
        ],
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == -32600