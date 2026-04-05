from datetime import datetime, timezone

import pytest

from app.services.portfolio_ytd import calculate_portfolio_ytd_metrics


@pytest.mark.asyncio
async def test_calculate_portfolio_ytd_metrics_returns_complete_result_when_history_exists() -> None:
    async def performance_fetcher(ticker: str, asset_type: str | None):
        data = {
            "AAPL": {"ytd_return": 25.0, "current_price": 125.0, "historical_data_available": True},
            "MSFT": {"ytd_return": 10.0, "current_price": 220.0, "historical_data_available": True},
        }
        return data[ticker]

    result = await calculate_portfolio_ytd_metrics(
        current_holdings=[
            {"ticker": "AAPL", "quantity": 10, "current_price": 125.0, "market_value": 1250.0, "asset_type": "stock", "currency": "USD"},
            {"ticker": "MSFT", "quantity": 5, "current_price": 220.0, "market_value": 1100.0, "asset_type": "stock", "currency": "USD"},
        ],
        transactions=[
            {"transaction_type": "DEPOSIT", "price": 200.0, "transaction_date": datetime(2026, 1, 15, tzinfo=timezone.utc), "notes": "Contribution [Currency: USD]"},
            {"transaction_type": "BUY", "asset_ticker": "MSFT", "quantity": 2.0, "price": 200.0, "transaction_date": datetime(2026, 2, 1, tzinfo=timezone.utc), "asset_currency": "USD", "asset_type": "stock"},
        ],
        current_cash_balance=150.0,
        portfolio_currency="USD",
        display_currency="USD",
        exchange_rates={},
        performance_fetcher=performance_fetcher,
        as_of=datetime(2026, 4, 5, tzinfo=timezone.utc),
    )

    assert result["ytd_complete"] is True
    assert result["ytd_missing_tickers"] == []
    assert result["ytd_message"] is None
    assert round(result["ytd_gain"], 2) == 350.0
    assert round(result["ytd_return_percentage"], 2) == 17.95


@pytest.mark.asyncio
async def test_calculate_portfolio_ytd_metrics_reports_missing_history_when_needed() -> None:
    async def performance_fetcher(ticker: str, asset_type: str | None):
        return {"ytd_return": None, "current_price": 40.0, "historical_data_available": False}

    result = await calculate_portfolio_ytd_metrics(
        current_holdings=[
            {"ticker": "PHN9756.CF", "quantity": 100, "current_price": 40.0, "market_value": 4000.0, "asset_type": "mutual_fund", "currency": "USD"},
        ],
        transactions=[],
        current_cash_balance=0.0,
        portfolio_currency="USD",
        display_currency="USD",
        exchange_rates={},
        performance_fetcher=performance_fetcher,
        as_of=datetime(2026, 4, 5, tzinfo=timezone.utc),
    )

    assert result["ytd_complete"] is False
    assert result["ytd_return_percentage"] is None
    assert result["ytd_gain"] is None
    assert result["ytd_missing_tickers"] == ["PHN9756.CF"]
    assert "PHN9756.CF" in result["ytd_message"]