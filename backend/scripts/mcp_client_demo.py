"""Simple MCP client demo for the embedded portfolio manager server."""

from __future__ import annotations

import argparse
import json
from typing import Any

import httpx


def call_rpc(base_url: str, payload: dict[str, Any], token: str | None = None) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = httpx.post(base_url, json=payload, headers=headers, timeout=30.0)
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo MCP client for the portfolio manager server")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/mcp", help="MCP endpoint URL")
    parser.add_argument("--token", default=None, help="Bearer token for authenticated tools")
    args = parser.parse_args()

    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"clientInfo": {"name": "demo-client", "version": "1.0.0"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "exchange_convert",
                "arguments": {"amount": 100, "from_currency": "USD", "to_currency": "CAD"},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "holdings_open_create_form", "arguments": {"ticker": "AAPL"}},
        },
        {"jsonrpc": "2.0", "id": 5, "method": "resources/read", "params": {"uri": "system://health"}},
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "prompts/get",
            "params": {
                "name": "portfolio.analysis.summary",
                "arguments": {"question": "Summarize my portfolio risk profile.", "currency": "USD"},
            },
        },
    ]

    for payload in requests:
        result = call_rpc(args.base_url, payload, token=args.token)
        print(f"\n=== {payload['method']} ===")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()