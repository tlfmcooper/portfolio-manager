#!/usr/bin/env python3
"""Migration script to create the per-user MCP API keys schema."""

from __future__ import annotations

import asyncio

from sqlalchemy import inspect

from app.core.database import engine
from app.models.mcp_api_key import MCPAPIKey


REQUIRED_COLUMNS = {column.name for column in MCPAPIKey.__table__.columns}


def _sanitize_database_url(url: str) -> str:
    if "@" not in url:
        return url
    scheme, _, host = url.rpartition("@")
    if "://" not in scheme:
        return url
    prefix = scheme.split("://", 1)[0]
    return f"{prefix}://***@{host}"


def _apply_migration(sync_conn) -> None:
    inspector = inspect(sync_conn)
    table_name = MCPAPIKey.__tablename__

    if table_name not in inspector.get_table_names():
        print(f"[+] Creating {table_name} table...")
        MCPAPIKey.__table__.create(bind=sync_conn, checkfirst=True)
        print(f"    [OK] {table_name} table created")
        return

    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    missing_columns = sorted(REQUIRED_COLUMNS - existing_columns)
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise RuntimeError(
            f"Existing {table_name} table is missing required columns: {missing}. "
            "Add them manually before re-running this migration."
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
    for index in MCPAPIKey.__table__.indexes:
        if index.name and index.name not in existing_indexes:
            print(f"[+] Creating missing index {index.name}...")
            index.create(bind=sync_conn, checkfirst=True)
            print(f"    [OK] {index.name} created")

    print(f"[INFO] {table_name} table already exists with the required columns")


async def migrate_mcp_api_keys() -> None:
    print(f"[INFO] Migrating database: {_sanitize_database_url(engine.url.render_as_string(hide_password=False))}")
    async with engine.begin() as conn:
        await conn.run_sync(_apply_migration)
    print("[SUCCESS] MCP API key migration completed successfully")


if __name__ == "__main__":
    asyncio.run(migrate_mcp_api_keys())