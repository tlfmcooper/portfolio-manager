from datetime import datetime
from urllib.parse import quote

import pytest
from requests.cookies import RequestsCookieJar

from app.services import finance_service
from app.services.finance_service import FinanceService


class _FakeResponse:
    def __init__(self, *, text: str = "", json_data=None, status_code: int = 200):
        self.text = text
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise finance_service.requests.HTTPError(f"status={self.status_code}")

    def json(self):
        return self._json_data


class _FakeSession:
    def __init__(self):
        self.cookies = RequestsCookieJar()
        self.calls = []

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append({
            "url": url,
            "headers": headers or {},
            "params": params,
            "timeout": timeout,
        })

        if "price-history/historical" in url:
            self.cookies.set("XSRF-TOKEN", quote("test-xsrf-token"))
            return _FakeResponse(text="<html></html>")

        if "/proxies/core-api/v1/historical/get" in url:
            return _FakeResponse(
                json_data={
                    "data": [
                        {"raw": {"tradeTime": "2026-01-02", "lastPrice": 100.0}},
                        {"raw": {"tradeTime": "2026-04-02", "lastPrice": 120.0}},
                    ]
                }
            )

        raise AssertionError(f"Unexpected URL requested: {url}")


@pytest.mark.asyncio
async def test_get_mutual_fund_history_uses_barchart_proxy_with_xsrf(monkeypatch) -> None:
    fake_session = _FakeSession()
    monkeypatch.setattr(finance_service, "session", fake_session)

    rows = await FinanceService._get_mutual_fund_history("PHN9756.CF", limit=400)

    assert rows is not None
    assert len(rows) == 2
    assert len(fake_session.calls) == 2
    assert fake_session.calls[0]["url"].endswith("/PHN9756.CF/price-history/historical")
    assert fake_session.calls[1]["url"] == "https://www.barchart.com/proxies/core-api/v1/historical/get"
    assert fake_session.calls[1]["headers"]["X-XSRF-TOKEN"] == "test-xsrf-token"
    assert fake_session.calls[1]["headers"]["Referer"].endswith("/PHN9756.CF/price-history/historical")
    assert fake_session.calls[1]["params"]["symbol"] == "PHN9756.CF"
    assert fake_session.calls[1]["params"]["orderDir"] == "asc"


@pytest.mark.asyncio
async def test_calculate_ticker_performance_uses_barchart_history_for_mutual_funds(monkeypatch) -> None:
    fixed_now = datetime(2026, 4, 5)

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now
            return fixed_now.astimezone(tz)

    async def fake_history(_ticker: str, limit: int = 400):
        assert limit == 400
        return [
            {"raw": {"tradeTime": "2025-04-07", "lastPrice": 80.0}},
            {"raw": {"tradeTime": "2026-01-02", "lastPrice": 100.0}},
            {"raw": {"tradeTime": "2026-01-05", "lastPrice": 105.0}},
            {"raw": {"tradeTime": "2026-03-05", "lastPrice": 110.0}},
            {"raw": {"tradeTime": "2026-04-02", "lastPrice": 120.0}},
        ]

    monkeypatch.setattr(finance_service, "datetime", _FixedDateTime)
    monkeypatch.setattr(FinanceService, "_get_mutual_fund_history", fake_history)

    result = await FinanceService.calculate_ticker_performance(
        "PHN9756.CF",
        asset_type="mutual_fund",
        periods=["ytd", "1m", "3m", "1y"],
    )

    assert result["data_source"] == "barchart"
    assert result["historical_data_available"] is True
    assert result["current_price"] == 120.0
    assert result["ytd_return"] == 20.0
    assert result["one_month_return"] == 9.09
    assert result["three_month_return"] == 14.29
    assert result["one_year_return"] == 50.0