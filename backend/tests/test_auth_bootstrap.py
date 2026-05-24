import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models import Portfolio, User
from main import create_application


@pytest_asyncio.fixture
async def bootstrap_client(tmp_path):
    database_path = tmp_path / "auth-bootstrap.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}", future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_application()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


async def create_test_user(session_factory, *, with_portfolio: bool):
    async with session_factory() as session:
        user = User(
            username="bootstrap_user",
            email="bootstrap@example.com",
            hashed_password="not-used",
        )
        session.add(user)
        await session.flush()

        portfolio = None
        if with_portfolio:
            portfolio = Portfolio(
                user_id=user.id,
                name="Bootstrap Portfolio",
                currency="USD",
            )
            session.add(portfolio)

        await session.commit()
        await session.refresh(user)
        if portfolio:
            await session.refresh(portfolio)

        return user, portfolio


@pytest.mark.asyncio
async def test_auth_bootstrap_returns_user_and_portfolio_id(bootstrap_client) -> None:
    client, session_factory = bootstrap_client
    user, portfolio = await create_test_user(session_factory, with_portfolio=True)
    token = create_access_token({"sub": user.username})

    response = await client.get(
        "/api/v1/auth/bootstrap",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["id"] == user.id
    assert payload["user"]["username"] == user.username
    assert payload["portfolio_id"] == portfolio.id
    assert payload["is_onboarded"] is True


@pytest.mark.asyncio
async def test_auth_bootstrap_handles_user_without_portfolio(bootstrap_client) -> None:
    client, session_factory = bootstrap_client
    user, _ = await create_test_user(session_factory, with_portfolio=False)
    token = create_access_token({"sub": user.username})

    response = await client.get(
        "/api/v1/auth/bootstrap",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["portfolio_id"] is None
    assert payload["is_onboarded"] is False


@pytest.mark.asyncio
async def test_auth_bootstrap_requires_authentication(bootstrap_client) -> None:
    client, _ = bootstrap_client

    response = await client.get("/api/v1/auth/bootstrap")

    assert response.status_code == 401
