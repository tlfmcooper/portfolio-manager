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


# ── _extract_ytd_from_raw_data ──────────────────────────────────────────────


def test_extract_ytd_uses_ytd_percent_change_field():
    raw = {"lastPrice": 45.03, "ytdPercentChange": 5.25}
    result = FinanceService._extract_ytd_from_raw_data(raw, 45.03)
    assert result == 5.25


def test_extract_ytd_uses_previous_year_close_when_percent_absent():
    raw = {"lastPrice": 45.03, "previousYearClose": 42.0}
    result = FinanceService._extract_ytd_from_raw_data(raw, 45.03)
    assert result == round((45.03 - 42.0) / 42.0 * 100, 2)


def test_extract_ytd_returns_none_when_no_ytd_fields():
    raw = {"lastPrice": 45.03, "previousPrice": 44.80}
    result = FinanceService._extract_ytd_from_raw_data(raw, 45.03)
    assert result is None


# ── _get_mutual_fund_info with ytd_return ────────────────────────────────────


def _make_barchart_quote_html(raw_fields: dict) -> str:
    """Build minimal Barchart quote HTML the existing parser can handle.

    The parser does:
      re.findall(r"{.*}", str(div))  →  ast.literal_eval  →  result[2]['raw']
    A single-line tuple expression satisfies all three steps.
    """
    raw_repr = repr(raw_fields)
    content = f"{{'meta': 'a'}}, {{'other': 'b'}}, {{'raw': {raw_repr}}}"
    return (
        '<html><body>'
        '<div class="bc-quote-overview row">'
        f'{content}'
        '</div></body></html>'
    )


@pytest.mark.asyncio
async def test_get_mutual_fund_info_returns_ytd_from_ytd_percent_change(monkeypatch):
    html = _make_barchart_quote_html(
        {"lastPrice": 45.03, "previousPrice": 44.80, "ytdPercentChange": 5.25}
    )

    class _Resp:
        text = html
        def raise_for_status(self): pass

    class _Sess:
        cookies = type("C", (), {"get": staticmethod(lambda k: None)})()
        def get(self, url, **kw): return _Resp()

    monkeypatch.setattr(finance_service, "session", _Sess())
    result = await FinanceService._get_mutual_fund_info("PHN9756.CF")

    assert result is not None
    assert result["current_price"] == 45.03
    assert result["ytd_return"] == 5.25


@pytest.mark.asyncio
async def test_get_mutual_fund_info_returns_ytd_from_previous_year_close(monkeypatch):
    html = _make_barchart_quote_html(
        {"lastPrice": 45.03, "previousPrice": 44.80, "previousYearClose": 42.0}
    )

    class _Resp:
        text = html
        def raise_for_status(self): pass

    class _Sess:
        cookies = type("C", (), {"get": staticmethod(lambda k: None)})()
        def get(self, url, **kw): return _Resp()

    monkeypatch.setattr(finance_service, "session", _Sess())
    result = await FinanceService._get_mutual_fund_info("PHN9756.CF")

    assert result is not None
    assert result["ytd_return"] == round((45.03 - 42.0) / 42.0 * 100, 2)


@pytest.mark.asyncio
async def test_get_mutual_fund_info_ytd_return_is_none_when_no_ytd_fields(monkeypatch):
    html = _make_barchart_quote_html(
        {"lastPrice": 45.03, "previousPrice": 44.80}
    )

    class _Resp:
        text = html
        def raise_for_status(self): pass

    class _Sess:
        cookies = type("C", (), {"get": staticmethod(lambda k: None)})()
        def get(self, url, **kw): return _Resp()

    monkeypatch.setattr(finance_service, "session", _Sess())
    result = await FinanceService._get_mutual_fund_info("PHN9756.CF")

    assert result is not None
    assert result.get("ytd_return") is None


@pytest.mark.asyncio
async def test_calculate_ticker_performance_uses_quote_page_ytd_without_calling_history_api(
    monkeypatch,
):
    history_calls = []

    async def fake_get_mutual_fund_info(ticker):
        return {"current_price": 45.03, "ytd_return": 5.25}

    async def fake_get_mutual_fund_history(ticker, limit=400):
        history_calls.append(ticker)
        return None

    monkeypatch.setattr(FinanceService, "_get_mutual_fund_info", fake_get_mutual_fund_info)
    monkeypatch.setattr(FinanceService, "_get_mutual_fund_history", fake_get_mutual_fund_history)

    result = await FinanceService.calculate_ticker_performance(
        "PHN9756.CF", asset_type="mutual_fund", periods=["ytd"]
    )

    assert result["ytd_return"] == 5.25
    assert result["current_price"] == 45.03
    assert result["historical_data_available"] is True
    assert history_calls == [], "history API must not be called when quote page has YTD"


@pytest.mark.asyncio
async def test_calculate_ticker_performance_falls_back_to_history_when_quote_page_lacks_ytd(
    monkeypatch,
):
    fixed_now = datetime(2026, 4, 5)

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz is None else fixed_now.astimezone(tz)

    async def fake_get_mutual_fund_info(ticker):
        return {"current_price": None, "ytd_return": None}

    async def fake_get_mutual_fund_history(ticker, limit=400):
        return [
            {"raw": {"tradeTime": "2026-01-02", "lastPrice": 100.0}},
            {"raw": {"tradeTime": "2026-04-02", "lastPrice": 120.0}},
        ]

    monkeypatch.setattr(finance_service, "datetime", _FixedDatetime)
    monkeypatch.setattr(FinanceService, "_get_mutual_fund_info", fake_get_mutual_fund_info)
    monkeypatch.setattr(FinanceService, "_get_mutual_fund_history", fake_get_mutual_fund_history)

    result = await FinanceService.calculate_ticker_performance(
        "PHN9756.CF", asset_type="mutual_fund", periods=["ytd"]
    )

    assert result["ytd_return"] == 20.0
    assert result["current_price"] == 120.0


@pytest.mark.asyncio
async def test_calculate_ticker_performance_uses_history_for_non_ytd_periods_even_when_quote_has_ytd(
    monkeypatch,
):
    fixed_now = datetime(2026, 4, 5)

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz is None else fixed_now.astimezone(tz)

    async def fake_get_mutual_fund_info(ticker):
        return {"current_price": 120.0, "ytd_return": 20.0}

    async def fake_get_mutual_fund_history(ticker, limit=400):
        return [
            {"raw": {"tradeTime": "2026-01-02", "lastPrice": 100.0}},
            {"raw": {"tradeTime": "2026-03-05", "lastPrice": 110.0}},
            {"raw": {"tradeTime": "2026-04-02", "lastPrice": 120.0}},
        ]

    monkeypatch.setattr(finance_service, "datetime", _FixedDatetime)
    monkeypatch.setattr(FinanceService, "_get_mutual_fund_info", fake_get_mutual_fund_info)
    monkeypatch.setattr(FinanceService, "_get_mutual_fund_history", fake_get_mutual_fund_history)

    result = await FinanceService.calculate_ticker_performance(
        "PHN9756.CF", asset_type="mutual_fund", periods=["ytd", "1m", "3m"]
    )

    assert result["ytd_return"] == 20.0
    assert result["one_month_return"] is not None
    assert result["three_month_return"] is not None


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

    async def fake_get_mutual_fund_info(_ticker):
        return {"current_price": None, "ytd_return": None}

    monkeypatch.setattr(finance_service, "datetime", _FixedDateTime)
    monkeypatch.setattr(FinanceService, "_get_mutual_fund_info", fake_get_mutual_fund_info)
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