from types import SimpleNamespace

from app.api.v1.portfolios import _build_summary_from_live_market


def test_build_summary_from_live_market_matches_live_holdings_math() -> None:
    portfolio = SimpleNamespace(
        id=1,
        name="My Portfolio",
        currency="USD",
        diversification_score=0.82,
        updated_at="2026-04-05T00:00:00+00:00",
    )
    live_payload = {
        "holdings": [
            {"market_value": 1200.0, "cost_basis": 1000.0},
            {"market_value": 800.0, "cost_basis": 1000.0},
        ],
        "cash_balance": 50.0,
        "display_currency": "USD",
        "updated_at": "2026-04-05T10:45:00+00:00",
    }

    summary = _build_summary_from_live_market(portfolio, live_payload)

    assert summary["total_value"] == 2050.0
    assert summary["total_return"] == 0.0
    assert summary["total_return_percentage"] == 0.0
    assert summary["cash_balance"] == 50.0
    assert summary["total_holdings_count"] == 2
    assert summary["currency"] == "USD"
    assert summary["last_updated"] == "2026-04-05T10:45:00+00:00"


def test_build_summary_from_live_market_uses_live_gain_loss() -> None:
    portfolio = SimpleNamespace(
        id=1,
        name="My Portfolio",
        currency="USD",
        diversification_score=1.0,
        updated_at="2026-04-05T00:00:00+00:00",
    )
    live_payload = {
        "holdings": [
            {"market_value": 1500.0, "cost_basis": 1000.0},
            {"market_value": 500.0, "cost_basis": 250.0},
        ],
        "cash_balance": 25.0,
        "display_currency": "USD",
        "updated_at": "2026-04-05T10:45:00+00:00",
    }

    summary = _build_summary_from_live_market(portfolio, live_payload)

    assert summary["total_value"] == 2025.0
    assert summary["total_return"] == 750.0
    assert round(summary["total_return_percentage"], 2) == 60.0