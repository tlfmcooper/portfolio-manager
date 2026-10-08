import csv
import io
from datetime import datetime, timezone
import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models import Asset, Holding, Portfolio, Transaction, User
from app.models.transaction import TransactionType
from app.services import portfolio_snapshot
from main import create_application


@pytest_asyncio.fixture
async def planning_client(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'planning.db'}")
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with sessions() as db:
        owner = User(username="planner", email="planner@test.com", hashed_password="unused")
        other = User(username="other", email="other@test.com", hashed_password="unused")
        db.add_all([owner, other]); await db.flush()
        portfolio = Portfolio(user_id=owner.id, name="Plan", currency="USD", cash_balance=200)
        db.add(portfolio); await db.flush()
        for ticker, qty, price in [("AAA", 6, 100), ("BBB", 4, 50)]:
            asset = Asset(ticker=ticker, name=ticker, currency="USD", asset_type="stock", current_price=price, last_price_update=datetime.now(timezone.utc))
            db.add(asset); await db.flush()
            db.add(Holding(portfolio_id=portfolio.id, asset_id=asset.id, ticker=ticker, quantity=qty, average_cost=price - 10, current_price=price))
        for i in range(105):
            db.add(Transaction(portfolio_id=portfolio.id, transaction_type=TransactionType.DEPOSIT, price=1, notes="=HYPERLINK(\"bad\")" if i == 0 else "deposit"))
        await db.commit()
        portfolio_id = portfolio.id

    class FX:
        async def get_exchange_rate(self, source, target, **kwargs):
            assert kwargs["strict"] is True
            return 1.4 if target == "CAD" else 1 / 1.4

    monkeypatch.setattr(portfolio_snapshot, "get_exchange_rate_service", lambda: FX())
    app = create_application()
    async def get_session():
        async with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = get_session
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client, {"Authorization": f"Bearer {create_access_token({'sub': 'planner'})}"}, portfolio_id
    await engine.dispose()


@pytest.mark.asyncio
async def test_snapshot_uses_stored_prices_and_separates_currencies(planning_client):
    client, headers, _ = planning_client
    response = await client.get("/api/v1/portfolios/snapshot", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_value"] == 1000
    assert data["unrealized_gain_loss"] == 100
    assert data["cash_balance"] == 200
    assert data["estimated_prices"] == 0
    converted = await client.get("/api/v1/portfolios/snapshot?currency=CAD", headers=headers)
    assert converted.json()["total_value"] == 1400
    assert converted.json()["holdings"][0]["asset_currency"] == "USD"


@pytest.mark.asyncio
async def test_targets_persist_and_validate_owned_holdings(planning_client):
    client, headers, _ = planning_client
    response = await client.put("/api/v1/portfolios/targets", headers=headers, json={"weights": {"AAA": 40, "BBB": 40, "CASH": 20}})
    assert response.status_code == 200
    data = (await client.get("/api/v1/portfolios/snapshot", headers=headers)).json()
    assert [h["target_allocation"] for h in data["holdings"]] == [40, 40]
    for weights in [{"AAA": 80, "CASH": 20.01}, {"AAA": 90, "CASH": 20}, {"AAA": -1, "CASH": 101}, {"UNKNOWN": 50, "CASH": 50}, {"AAA": 100}]:
        assert (await client.put("/api/v1/portfolios/targets", headers=headers, json={"weights": weights})).status_code == 422


@pytest.mark.asyncio
async def test_exports_include_all_transactions_and_escape_formulas(planning_client):
    client, headers, _ = planning_client
    response = await client.get("/api/v1/portfolios/export?kind=transactions", headers=headers)
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.text.lstrip('\ufeff'))))
    assert len(rows) == 106
    assert rows[1][-1].startswith("'=HYPERLINK")
    assert response.headers["cache-control"] == "no-store"
    holdings = await client.get("/api/v1/portfolios/export?kind=holdings&currency=CAD", headers=headers)
    rows = list(csv.reader(io.StringIO(holdings.text.lstrip('\ufeff'))))
    assert rows[-1][0] == "CASH"
    assert rows[-1][-1] == "CAD"
    assert float(rows[-1][5]) == 280


@pytest.mark.asyncio
async def test_new_routes_and_analytics_require_account_ownership(planning_client):
    client, headers, portfolio_id = planning_client
    for endpoint in ["/portfolios/snapshot", "/portfolios/export", f"/analysis/portfolios/{portfolio_id}/metrics"]:
        assert (await client.get('/api/v1' + endpoint)).status_code == 401
    other_headers = {"Authorization": f"Bearer {create_access_token({'sub': 'other'})}"}
    assert (await client.get('/api/v1/portfolios/snapshot', headers=other_headers)).status_code == 404
    assert (await client.get(f'/api/v1/analysis/portfolios/{portfolio_id}/metrics', headers=other_headers)).status_code == 404
    assert (await client.get('/api/v1/portfolios/snapshot?currency=EUR', headers=headers)).status_code == 422


@pytest.mark.asyncio
async def test_snapshot_does_not_invent_fx_when_provider_is_unavailable(planning_client, monkeypatch):
    client, headers, _ = planning_client
    class FailedFX:
        async def get_exchange_rate(self, *args, **kwargs):
            raise ValueError('unavailable')
    monkeypatch.setattr(portfolio_snapshot, 'get_exchange_rate_service', lambda: FailedFX())
    assert (await client.get('/api/v1/portfolios/snapshot?currency=CAD', headers=headers)).status_code == 503


def test_snapshot_quote_uses_its_own_timestamp_and_discloses_estimates():
    from types import SimpleNamespace
    from app.services.portfolio_snapshot import stored_price
    old = datetime(2026, 10, 7)
    latest = datetime(2026, 10, 8)
    holding = SimpleNamespace(current_price=100, last_price_update=old,
                              average_cost=90, asset=SimpleNamespace(current_price=110, last_price_update=latest))
    price, timestamp, estimated = stored_price(holding)
    assert price == 110
    assert timestamp.tzinfo == timezone.utc
    assert estimated is False
    holding.asset.current_price = None
    holding.current_price = None
    assert stored_price(holding) == (90, None, True)
