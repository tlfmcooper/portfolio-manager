#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite to Supabase PostgreSQL.

This script:
1. Reads all data from the local SQLite database (portfolio.db)
2. Creates tables in Supabase PostgreSQL
3. Migrates all data preserving relationships and IDs

Usage:
    python migrate_to_supabase.py

Requirements:
    - DIRECT_URL environment variable set in .env (Supabase direct connection)
    - SQLite database file (portfolio.db) in the backend directory
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

import aiosqlite
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool


def parse_datetime(value: Any) -> Optional[datetime]:
    """Convert a string or None to a datetime object."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # Try common datetime formats
        formats = [
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


# Get database URLs
SQLITE_PATH = Path(__file__).parent / "portfolio.db"
DIRECT_URL = os.getenv("DIRECT_URL")

if not DIRECT_URL:
    print("ERROR: DIRECT_URL environment variable not set.")
    print("Please add DIRECT_URL to your .env file with the Supabase direct connection string.")
    sys.exit(1)


def parse_and_fix_postgres_url(url: str) -> str:
    """
    Parse PostgreSQL URL and properly URL-encode the password.
    Handles passwords containing special characters like @, #, !, etc.
    """
    from urllib.parse import quote_plus, urlparse, urlunparse

    # Convert postgres:// to postgresql+asyncpg://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    # Parse the URL
    # Format: postgresql://user:password@host:port/database
    # Problem: password may contain @ which confuses parsing

    if not url.startswith("postgresql://"):
        return url

    # Remove scheme
    rest = url.replace("postgresql://", "")

    # Find the last @ which separates credentials from host
    # (passwords may contain @, but host won't have @ before it)
    last_at_idx = rest.rfind("@")
    if last_at_idx == -1:
        # No credentials
        return f"postgresql+asyncpg://{rest}"

    credentials = rest[:last_at_idx]
    host_and_db = rest[last_at_idx + 1:]

    # Split credentials into user and password
    first_colon_idx = credentials.find(":")
    if first_colon_idx == -1:
        # No password
        user = credentials
        password = ""
    else:
        user = credentials[:first_colon_idx]
        password = credentials[first_colon_idx + 1:]

    # URL-encode the password to handle special characters
    encoded_password = quote_plus(password)

    # Reconstruct URL with asyncpg driver
    if password:
        return f"postgresql+asyncpg://{user}:{encoded_password}@{host_and_db}"
    else:
        return f"postgresql+asyncpg://{user}@{host_and_db}"


POSTGRES_URL = parse_and_fix_postgres_url(DIRECT_URL)


async def get_sqlite_data():
    """Read all data from SQLite database."""
    if not SQLITE_PATH.exists():
        print(f"ERROR: SQLite database not found at {SQLITE_PATH}")
        sys.exit(1)

    print(f"Reading data from SQLite: {SQLITE_PATH}")

    data = {
        "users": [],
        "assets": [],
        "portfolios": [],
        "holdings": [],
        "transactions": [],
    }

    async with aiosqlite.connect(SQLITE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Read users
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            data["users"] = [dict(row) for row in rows]
            print(f"  Found {len(data['users'])} users")

        # Read assets
        async with db.execute("SELECT * FROM assets") as cursor:
            rows = await cursor.fetchall()
            data["assets"] = [dict(row) for row in rows]
            print(f"  Found {len(data['assets'])} assets")

        # Read portfolios
        async with db.execute("SELECT * FROM portfolios") as cursor:
            rows = await cursor.fetchall()
            data["portfolios"] = [dict(row) for row in rows]
            print(f"  Found {len(data['portfolios'])} portfolios")

        # Read holdings
        async with db.execute("SELECT * FROM holdings") as cursor:
            rows = await cursor.fetchall()
            data["holdings"] = [dict(row) for row in rows]
            print(f"  Found {len(data['holdings'])} holdings")

        # Read transactions
        async with db.execute("SELECT * FROM transactions") as cursor:
            rows = await cursor.fetchall()
            data["transactions"] = [dict(row) for row in rows]
            print(f"  Found {len(data['transactions'])} transactions")

    return data


async def create_postgres_tables(engine):
    """Create all tables in PostgreSQL using raw SQL."""
    print("\nCreating tables in Supabase PostgreSQL...")

    # Define tables using raw SQL to avoid importing app modules
    # which would try to connect to the database with the app's engine
    create_tables_sql = """
    -- Drop existing tables (in reverse order of dependencies)
    DROP TABLE IF EXISTS transactions CASCADE;
    DROP TABLE IF EXISTS holdings CASCADE;
    DROP TABLE IF EXISTS portfolios CASCADE;
    DROP TABLE IF EXISTS assets CASCADE;
    DROP TABLE IF EXISTS users CASCADE;
    DROP TYPE IF EXISTS transactiontype CASCADE;

    -- Create enum type for transactions
    CREATE TYPE transactiontype AS ENUM ('BUY', 'SELL', 'DEPOSIT', 'WITHDRAWAL');

    -- Create users table
    CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        full_name VARCHAR(100),
        is_active BOOLEAN DEFAULT TRUE NOT NULL,
        is_superuser BOOLEAN DEFAULT FALSE NOT NULL,
        bio TEXT,
        avatar_url VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        last_login TIMESTAMP WITH TIME ZONE
    );
    CREATE INDEX ix_users_id ON users(id);
    CREATE INDEX ix_users_username ON users(username);
    CREATE INDEX ix_users_email ON users(email);

    -- Create assets table
    CREATE TABLE assets (
        id SERIAL PRIMARY KEY,
        ticker VARCHAR(20) UNIQUE NOT NULL,
        name VARCHAR(200),
        asset_type VARCHAR(50),
        sector VARCHAR(100),
        industry VARCHAR(100),
        description TEXT,
        currency VARCHAR(3) DEFAULT 'USD' NOT NULL,
        exchange VARCHAR(50),
        is_active BOOLEAN DEFAULT TRUE NOT NULL,
        current_price FLOAT,
        market_cap FLOAT,
        dividend_yield FLOAT,
        pe_ratio FLOAT,
        beta FLOAT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        last_price_update TIMESTAMP WITH TIME ZONE
    );
    CREATE INDEX ix_assets_id ON assets(id);
    CREATE INDEX ix_assets_ticker ON assets(ticker);

    -- Create portfolios table
    CREATE TABLE portfolios (
        id SERIAL PRIMARY KEY,
        user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
        name VARCHAR(100) DEFAULT 'My Portfolio' NOT NULL,
        description TEXT,
        initial_value FLOAT DEFAULT 0.0 NOT NULL,
        currency VARCHAR(3) DEFAULT 'USD' NOT NULL,
        is_active BOOLEAN DEFAULT TRUE NOT NULL,
        risk_tolerance VARCHAR(20),
        investment_objective VARCHAR(50),
        time_horizon VARCHAR(20),
        total_invested FLOAT DEFAULT 0.0 NOT NULL,
        total_value FLOAT DEFAULT 0.0 NOT NULL,
        total_return FLOAT DEFAULT 0.0 NOT NULL,
        total_return_percentage FLOAT DEFAULT 0.0 NOT NULL,
        cash_balance FLOAT DEFAULT 0.0 NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        last_rebalance TIMESTAMP WITH TIME ZONE
    );
    CREATE INDEX ix_portfolios_id ON portfolios(id);

    -- Create holdings table
    CREATE TABLE holdings (
        id SERIAL PRIMARY KEY,
        portfolio_id INTEGER NOT NULL REFERENCES portfolios(id),
        asset_id INTEGER NOT NULL REFERENCES assets(id),
        ticker VARCHAR(20) NOT NULL,
        quantity FLOAT NOT NULL,
        average_cost FLOAT NOT NULL,
        current_price FLOAT,
        target_allocation FLOAT,
        cost_basis FLOAT,
        market_value FLOAT,
        unrealized_gain_loss FLOAT,
        unrealized_gain_loss_percentage FLOAT,
        notes TEXT,
        is_active BOOLEAN DEFAULT TRUE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        last_price_update TIMESTAMP WITH TIME ZONE,
        CONSTRAINT unique_portfolio_ticker UNIQUE (portfolio_id, ticker)
    );
    CREATE INDEX ix_holdings_id ON holdings(id);
    CREATE INDEX ix_holdings_ticker ON holdings(ticker);

    -- Create transactions table
    CREATE TABLE transactions (
        id SERIAL PRIMARY KEY,
        portfolio_id INTEGER NOT NULL REFERENCES portfolios(id),
        asset_id INTEGER REFERENCES assets(id),
        transaction_type transactiontype NOT NULL,
        quantity FLOAT,
        price FLOAT NOT NULL,
        transaction_date TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        notes VARCHAR,
        realized_gain_loss FLOAT
    );
    CREATE INDEX ix_transactions_id ON transactions(id);
    """

    async with engine.begin() as conn:
        # Execute all SQL statements
        for statement in create_tables_sql.split(';'):
            statement = statement.strip()
            if statement:
                await conn.execute(text(statement))

    print("  Tables created successfully")


async def migrate_data(engine, data):
    """Migrate data from SQLite to PostgreSQL."""
    print("\nMigrating data to Supabase PostgreSQL...")

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Migrate users
            if data["users"]:
                print("  Migrating users...")
                for user in data["users"]:
                    await session.execute(
                        text("""
                            INSERT INTO users (id, username, email, hashed_password, full_name,
                                             is_active, is_superuser, bio, avatar_url,
                                             created_at, updated_at, last_login)
                            VALUES (:id, :username, :email, :hashed_password, :full_name,
                                   :is_active, :is_superuser, :bio, :avatar_url,
                                   :created_at, :updated_at, :last_login)
                        """),
                        {
                            "id": user["id"],
                            "username": user["username"],
                            "email": user["email"],
                            "hashed_password": user["hashed_password"],
                            "full_name": user.get("full_name"),
                            "is_active": bool(user.get("is_active", True)),
                            "is_superuser": bool(user.get("is_superuser", False)),
                            "bio": user.get("bio"),
                            "avatar_url": user.get("avatar_url"),
                            "created_at": parse_datetime(user.get("created_at")),
                            "updated_at": parse_datetime(user.get("updated_at")),
                            "last_login": parse_datetime(user.get("last_login")),
                        }
                    )
                print(f"    Migrated {len(data['users'])} users")

            # Migrate assets
            if data["assets"]:
                print("  Migrating assets...")
                for asset in data["assets"]:
                    await session.execute(
                        text("""
                            INSERT INTO assets (id, ticker, name, asset_type, sector, industry,
                                              description, currency, exchange, is_active,
                                              current_price, market_cap, dividend_yield, pe_ratio, beta,
                                              created_at, updated_at, last_price_update)
                            VALUES (:id, :ticker, :name, :asset_type, :sector, :industry,
                                   :description, :currency, :exchange, :is_active,
                                   :current_price, :market_cap, :dividend_yield, :pe_ratio, :beta,
                                   :created_at, :updated_at, :last_price_update)
                        """),
                        {
                            "id": asset["id"],
                            "ticker": asset["ticker"],
                            "name": asset.get("name"),
                            "asset_type": asset.get("asset_type"),
                            "sector": asset.get("sector"),
                            "industry": asset.get("industry"),
                            "description": asset.get("description"),
                            "currency": asset.get("currency", "USD"),
                            "exchange": asset.get("exchange"),
                            "is_active": bool(asset.get("is_active", True)),
                            "current_price": asset.get("current_price"),
                            "market_cap": asset.get("market_cap"),
                            "dividend_yield": asset.get("dividend_yield"),
                            "pe_ratio": asset.get("pe_ratio"),
                            "beta": asset.get("beta"),
                            "created_at": parse_datetime(asset.get("created_at")),
                            "updated_at": parse_datetime(asset.get("updated_at")),
                            "last_price_update": parse_datetime(asset.get("last_price_update")),
                        }
                    )
                print(f"    Migrated {len(data['assets'])} assets")

            # Migrate portfolios
            if data["portfolios"]:
                print("  Migrating portfolios...")
                for portfolio in data["portfolios"]:
                    await session.execute(
                        text("""
                            INSERT INTO portfolios (id, user_id, name, description, initial_value,
                                                   currency, is_active, risk_tolerance, investment_objective,
                                                   time_horizon, total_invested, total_value, total_return,
                                                   total_return_percentage, cash_balance,
                                                   created_at, updated_at, last_rebalance)
                            VALUES (:id, :user_id, :name, :description, :initial_value,
                                   :currency, :is_active, :risk_tolerance, :investment_objective,
                                   :time_horizon, :total_invested, :total_value, :total_return,
                                   :total_return_percentage, :cash_balance,
                                   :created_at, :updated_at, :last_rebalance)
                        """),
                        {
                            "id": portfolio["id"],
                            "user_id": portfolio["user_id"],
                            "name": portfolio.get("name", "My Portfolio"),
                            "description": portfolio.get("description"),
                            "initial_value": portfolio.get("initial_value", 0.0),
                            "currency": portfolio.get("currency", "USD"),
                            "is_active": bool(portfolio.get("is_active", True)),
                            "risk_tolerance": portfolio.get("risk_tolerance"),
                            "investment_objective": portfolio.get("investment_objective"),
                            "time_horizon": portfolio.get("time_horizon"),
                            "total_invested": portfolio.get("total_invested", 0.0),
                            "total_value": portfolio.get("total_value", 0.0),
                            "total_return": portfolio.get("total_return", 0.0),
                            "total_return_percentage": portfolio.get("total_return_percentage", 0.0),
                            "cash_balance": portfolio.get("cash_balance", 0.0),
                            "created_at": parse_datetime(portfolio.get("created_at")),
                            "updated_at": parse_datetime(portfolio.get("updated_at")),
                            "last_rebalance": parse_datetime(portfolio.get("last_rebalance")),
                        }
                    )
                print(f"    Migrated {len(data['portfolios'])} portfolios")

            # Migrate holdings
            if data["holdings"]:
                print("  Migrating holdings...")
                for holding in data["holdings"]:
                    await session.execute(
                        text("""
                            INSERT INTO holdings (id, portfolio_id, asset_id, ticker, quantity,
                                                 average_cost, current_price, target_allocation,
                                                 cost_basis, market_value, unrealized_gain_loss,
                                                 unrealized_gain_loss_percentage, notes, is_active,
                                                 created_at, updated_at, last_price_update)
                            VALUES (:id, :portfolio_id, :asset_id, :ticker, :quantity,
                                   :average_cost, :current_price, :target_allocation,
                                   :cost_basis, :market_value, :unrealized_gain_loss,
                                   :unrealized_gain_loss_percentage, :notes, :is_active,
                                   :created_at, :updated_at, :last_price_update)
                        """),
                        {
                            "id": holding["id"],
                            "portfolio_id": holding["portfolio_id"],
                            "asset_id": holding["asset_id"],
                            "ticker": holding["ticker"],
                            "quantity": holding["quantity"],
                            "average_cost": holding["average_cost"],
                            "current_price": holding.get("current_price"),
                            "target_allocation": holding.get("target_allocation"),
                            "cost_basis": holding.get("cost_basis"),
                            "market_value": holding.get("market_value"),
                            "unrealized_gain_loss": holding.get("unrealized_gain_loss"),
                            "unrealized_gain_loss_percentage": holding.get("unrealized_gain_loss_percentage"),
                            "notes": holding.get("notes"),
                            "is_active": bool(holding.get("is_active", True)),
                            "created_at": parse_datetime(holding.get("created_at")),
                            "updated_at": parse_datetime(holding.get("updated_at")),
                            "last_price_update": parse_datetime(holding.get("last_price_update")),
                        }
                    )
                print(f"    Migrated {len(data['holdings'])} holdings")

            # Migrate transactions
            if data["transactions"]:
                print("  Migrating transactions...")
                for txn in data["transactions"]:
                    await session.execute(
                        text("""
                            INSERT INTO transactions (id, portfolio_id, asset_id, transaction_type,
                                                     quantity, price, transaction_date, notes,
                                                     realized_gain_loss)
                            VALUES (:id, :portfolio_id, :asset_id, :transaction_type,
                                   :quantity, :price, :transaction_date, :notes,
                                   :realized_gain_loss)
                        """),
                        {
                            "id": txn["id"],
                            "portfolio_id": txn["portfolio_id"],
                            "asset_id": txn.get("asset_id"),
                            "transaction_type": txn["transaction_type"],
                            "quantity": txn.get("quantity"),
                            "price": txn["price"],
                            "transaction_date": parse_datetime(txn.get("transaction_date")),
                            "notes": txn.get("notes"),
                            "realized_gain_loss": txn.get("realized_gain_loss"),
                        }
                    )
                print(f"    Migrated {len(data['transactions'])} transactions")

            # Update sequences to avoid ID conflicts for future inserts
            print("\n  Updating PostgreSQL sequences...")

            # Get max IDs and update sequences
            tables = ["users", "assets", "portfolios", "holdings", "transactions"]
            for table in tables:
                result = await session.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table}"))
                max_id = result.scalar()
                if max_id and max_id > 0:
                    await session.execute(
                        text(f"SELECT setval('{table}_id_seq', :max_id, true)"),
                        {"max_id": max_id}
                    )
                    print(f"    Set {table}_id_seq to {max_id}")

            await session.commit()
            print("\n  Data migration completed successfully!")

        except Exception as e:
            await session.rollback()
            print(f"\nERROR during migration: {e}")
            raise


async def verify_migration(engine):
    """Verify the migration by counting records."""
    print("\nVerifying migration...")

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        tables = ["users", "assets", "portfolios", "holdings", "transactions"]
        for table in tables:
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"  {table}: {count} records")


async def main():
    """Main migration function."""
    print("=" * 60)
    print("SQLite to Supabase PostgreSQL Migration")
    print("=" * 60)

    # Create PostgreSQL engine
    print(f"\nConnecting to Supabase PostgreSQL...")
    pg_url_safe = POSTGRES_URL.split("@")[1] if "@" in POSTGRES_URL else "configured"
    print(f"  Target: {pg_url_safe}")

    pg_engine = create_async_engine(
        POSTGRES_URL,
        poolclass=NullPool,
        echo=False,
    )

    try:
        # Test connection
        async with pg_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("  Connection successful!")
    except Exception as e:
        print(f"  ERROR: Could not connect to PostgreSQL: {e}")
        sys.exit(1)

    # Read SQLite data
    data = await get_sqlite_data()

    # Create tables in PostgreSQL
    await create_postgres_tables(pg_engine)

    # Migrate data
    await migrate_data(pg_engine, data)

    # Verify migration
    await verify_migration(pg_engine)

    await pg_engine.dispose()

    print("\n" + "=" * 60)
    print("Migration completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Update Railway environment variables:")
    print("   - Set DATABASE_URL to your Supabase connection string (Transaction mode)")
    print("2. Deploy to Railway")
    print("3. Test the /health endpoint to verify database connection")


if __name__ == "__main__":
    asyncio.run(main())
