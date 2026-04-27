import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1 import assets as assets_api
from app.core.database import Base
from app.models import Asset, Portfolio, Transaction, User
from app.models.transaction import TransactionType
from app.schemas.holding_extended import AssetSellRequest


class JsonRequest:
    headers = {"content-type": "application/json"}

    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


class ExchangeService:
    async def get_exchange_rate(self, source, target):
        rates = {
            ("CAD", "USD"): 0.75,
            ("USD", "CAD"): 1.25,
        }
        return rates.get((source, target), 1.0)


@pytest_asyncio.fixture
async def db_session(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'cash_transactions.db'}",
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def user_with_portfolio(db_session):
    user = User(
        username="cash-test",
        email="cash-test@example.com",
        hashed_password="not-used",
    )
    db_session.add(user)
    await db_session.flush()

    portfolio = Portfolio(
        user_id=user.id,
        name="Cash Test",
        currency="USD",
        cash_balance=1000.0,
    )
    db_session.add(portfolio)
    await db_session.commit()
    return user, portfolio


@pytest.fixture(autouse=True)
def patch_external_services(monkeypatch):
    async def fake_asset_info(ticker, asset_type="stock"):
        return {
            "ticker": ticker.upper(),
            "name": ticker.upper(),
            "asset_type": asset_type,
            "currency": "CAD" if ticker.upper().endswith(".TO") else "USD",
            "current_price": 10.0,
        }

    monkeypatch.setattr(assets_api.FinanceService, "get_asset_info", fake_asset_info)
    monkeypatch.setattr(
        "app.services.exchange_rate_service.get_exchange_rate_service",
        lambda: ExchangeService(),
    )


async def noop_cache_invalidation(portfolio_id):
    return None


@pytest.mark.asyncio
async def test_onboarding_snapshot_does_not_mutate_cash(db_session, user_with_portfolio):
    user, portfolio = user_with_portfolio
    payload = [
        {
            "ticker": "AAPL",
            "quantity": 2,
            "average_cost": 100,
            "asset_type": "stock",
            "currency": "USD",
        }
    ]

    response = await assets_api.onboard_asset(
        JsonRequest(payload),
        affect_cash=False,
        current_user=user,
        db=db_session,
    )

    await db_session.refresh(portfolio)
    assert response["assets"][0]["cash_affected"] is False
    assert portfolio.cash_balance == 1000.0


@pytest.mark.asyncio
async def test_buy_mode_debits_cash_and_allows_negative_balance(
    db_session,
    user_with_portfolio,
    monkeypatch,
):
    monkeypatch.setattr(assets_api, "invalidate_portfolio_transaction_caches", noop_cache_invalidation)
    user, portfolio = user_with_portfolio
    payload = [
        {
            "ticker": "MSFT",
            "quantity": 20,
            "average_cost": 75,
            "asset_type": "stock",
            "currency": "USD",
        }
    ]

    response = await assets_api.onboard_asset(
        JsonRequest(payload),
        affect_cash=True,
        current_user=user,
        db=db_session,
    )

    await db_session.refresh(portfolio)
    assert response["assets"][0]["cash_affected"] is True
    assert portfolio.cash_balance == -500.0


@pytest.mark.asyncio
async def test_buy_and_sell_apply_currency_conversion(
    db_session,
    user_with_portfolio,
    monkeypatch,
):
    monkeypatch.setattr(assets_api, "invalidate_portfolio_transaction_caches", noop_cache_invalidation)
    user, portfolio = user_with_portfolio

    await assets_api.onboard_asset(
        JsonRequest([
            {
                "ticker": "SHOP.TO",
                "quantity": 10,
                "average_cost": 20,
                "asset_type": "stock",
                "currency": "CAD",
            }
        ]),
        affect_cash=True,
        current_user=user,
        db=db_session,
    )
    await db_session.refresh(portfolio)
    assert portfolio.cash_balance == 850.0

    response = await assets_api.sell_asset(
        AssetSellRequest(ticker="SHOP.TO", quantity=4, price=30),
        current_user=user,
        db=db_session,
    )

    await db_session.refresh(portfolio)
    assert response["success"] is True
    assert response["sale_proceeds"] == 90.0
    assert portfolio.cash_balance == 940.0

    txn = await db_session.get(Transaction, response["transaction_id"])
    assert txn.transaction_type == TransactionType.SELL
    assert txn.quantity == 4

    asset = await db_session.get(Asset, txn.asset_id)
    assert asset.ticker == "SHOP.TO"
