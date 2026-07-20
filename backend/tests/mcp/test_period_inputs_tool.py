from types import SimpleNamespace

import pytest

from app.mcp import handlers
from app.mcp.handlers import HandlerContext
from app.services import portfolio_period_service


@pytest.mark.asyncio
async def test_period_inputs_tool_returns_facts_without_dashboard_ui(monkeypatch) -> None:
    portfolio = SimpleNamespace(id=7, currency="USD")
    captured = {}

    async def fake_current_portfolio(ctx):
        return SimpleNamespace(id=11), portfolio

    async def fake_build(db, selected_portfolio, start_date, end_date, currency):
        captured.update(
            {
                "portfolio": selected_portfolio,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "currency": currency,
            }
        )
        return {
            "requested_period": {},
            "effective_period": {},
            "currency": currency,
            "opening": {},
            "closing": {},
            "assets": [],
            "external_cash_flows": [],
            "net_external_cash_flow": 0,
            "calculation_contract": {"method": "modified_dietz"},
            "coverage": {"complete": True, "issues": []},
            "generated_at": "2026-07-19T00:00:00Z",
        }

    monkeypatch.setattr(handlers, "_get_current_portfolio", fake_current_portfolio)
    monkeypatch.setattr(
        portfolio_period_service,
        "build_portfolio_period_inputs",
        fake_build,
    )

    result = await handlers.tool_portfolio_get_period_inputs(
        HandlerContext(
            db=SimpleNamespace(),
            auth=SimpleNamespace(),
            request_id="request-1",
            rpc_method="tools/call",
        ),
        {
            "start_date": "2026-07-10",
            "end_date": "2026-07-17",
            "currency": "CAD",
        },
    )

    assert captured == {
        "portfolio": portfolio,
        "start_date": "2026-07-10",
        "end_date": "2026-07-17",
        "currency": "CAD",
    }
    assert result.structuredContent["calculation_contract"]["method"] == "modified_dietz"
    assert result.meta == {}


@pytest.mark.asyncio
async def test_period_inputs_tool_rejects_reversed_dates(monkeypatch) -> None:
    async def fake_current_portfolio(ctx):
        raise AssertionError("date validation must happen before database access")

    monkeypatch.setattr(handlers, "_get_current_portfolio", fake_current_portfolio)

    with pytest.raises(Exception, match="end_date must be on or after start_date"):
        await handlers.tool_portfolio_get_period_inputs(
            HandlerContext(
                db=SimpleNamespace(),
                auth=SimpleNamespace(),
                request_id="request-1",
                rpc_method="tools/call",
            ),
            {"start_date": "2026-07-20", "end_date": "2026-07-19"},
        )
