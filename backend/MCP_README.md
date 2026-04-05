# Portfolio Manager MCP Server

This repository now includes an embedded MCP server for the existing FastAPI backend. It exposes portfolio, holdings, market, exchange, resource, and prompt capabilities through JSON-RPC 2.0 and supports MCP Apps-style UI metadata for dashboards, forms, tables, and workflows.

Tool identifiers now follow the stricter lowercase MCP client convention using underscores, for example `portfolio_get_summary` and `exchange_convert`. The server still accepts the older dotted names as backward-compatible aliases for direct `tools/call` requests.

For the route-by-route plan to expose the dashboard's interactive surface through MCP Apps-style capabilities, see `MCP_FRONTEND_PARITY_PLAN.md` in the repository root.

The first frontend parity wave is now implemented for core portfolio operations, including cash balance reads, transaction history reads, holding edit and sell actions, cash deposit and withdrawal actions, live market board reads, and form schemas for create, edit, sell, and cash workflows.

The remaining protected-route parity is also now exposed through MCP for:

- overview dashboard aggregation
- analytics tab reads for risk, allocation, efficient frontier, Monte Carlo, and CPPI
- onboarding status plus manual and CSV onboarding import forms and actions

Settings parity for MCP access management is also now implemented through MCP tools and resources for listing, creating, rotating, and revoking per-user MCP API keys.

## What it provides

- Full MCP core method surface for:
  - `initialize`
  - `ping`
  - `tools/list`
  - `tools/call`
  - `resources/list`
  - `resources/read`
  - `resources/templates/list`
  - `resources/subscribe`
  - `resources/unsubscribe`
  - `prompts/list`
  - `prompts/get`
- `completion/complete` for prompt and resource argument suggestions.
- A `sampling/createMessage` helper for model interaction hints.
- `logging/setLevel` plus session-aware SSE log notifications through `notifications/message`.
- Config-driven capability discovery from JSON or YAML.
- Bearer-token and API-key aware auth handling.
- Tool-level permission checks.
- Structured logging with request IDs.
- Optional Streamable HTTP support with GET-based SSE streams, `Mcp-Session-Id` session tracking, and `DELETE /mcp` session termination.

## Files

- `backend/app/mcp/router.py`: JSON-RPC transport and dispatch.
- `backend/app/mcp/config.py`: capability config loader for JSON and YAML.
- `backend/app/mcp/registry.py`: runtime registry and schema validation.
- `backend/app/mcp/handlers.py`: tool, resource, prompt, and Apps UI handlers.
- `backend/app/mcp/default_capabilities.json`: default production capability set.
- `backend/app/mcp/example_capabilities.yaml`: example YAML variant.
- `backend/scripts/mcp_client_demo.py`: sample client workflow.

## Frontend Parity Coverage

Protected-route parity is now available through MCP for:

- overview: `overview_get_dashboard`, `overview://dashboard/current`
- portfolio: summary, holdings, cash balance, transactions, buy, sell, edit, deposit, withdraw
- analytics: `analytics_get_risk`, `analytics_get_allocation`, `analytics_get_efficient_frontier`, `analytics_get_monte_carlo`, `analytics_get_cppi`
- live market: quotes and portfolio live board
- settings: list, create, rotate, revoke per-user MCP API keys
- onboarding: `onboarding_get_status`, `onboarding_open_manual_form`, `onboarding_open_csv_import_form`, `onboarding_import_assets`, `onboarding_import_csv`

The main remaining gap is not MCP surface area but the behavior of the underlying analytics and market-data services, which still depend on the existing backend data and external quote infrastructure.

## Setup

1. Install backend dependencies.

```bash
cd backend
pip install -r requirements.txt
```

2. Set required environment variables.

```bash
export FINNHUB_API_KEY=your_finnhub_key
export SECRET_KEY=your_secret_key
export MCP_ENABLED=true
export MCP_ROUTE_PREFIX=/mcp
export MCP_PROTOCOL_VERSION=2025-03-26
```

3. Optional: switch to the YAML capability file.

```bash
export MCP_CONFIG_PATH=backend/app/mcp/example_capabilities.yaml
```

4. Recommended: create a per-user MCP API key from a logged-in session.

Use the normal auth API to sign in, then create a key from the user profile endpoint:

```bash
curl -s http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=demo&password=your-password'

curl -s http://127.0.0.1:8000/api/v1/users/me/mcp-api-keys \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <access-token>' \
  -d '{"name":"VS Code MCP","expires_in_days":365}'
```

The response returns the raw `api_key` exactly once. Store that in your MCP client config as `x-mcp-api-key`.

5. Optional: configure legacy service API keys for non-user-scoped clients.

```bash
export MCP_API_KEYS_JSON='{"local-demo-key": ["exchange:read", "market:read", "resources:read", "prompts:read"]}'
```

For portfolio and holdings tools, bind the API key to a real backend username:

```bash
export MCP_API_KEYS_JSON='{"local-portfolio-key": {"username": "demo", "permissions": ["portfolio:read", "portfolio:write", "holdings:read", "holdings:write", "workflow:use", "resources:read", "prompts:read", "market:read", "exchange:read"]}}'
```

6. Start the backend.

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The MCP server is available at `http://127.0.0.1:8000/mcp`.

## Spec Coverage Notes

- Server-side completions are implemented for prompt and resource arguments.
- `notifications/initialized` is accepted and `initialize` is rejected when sent in a JSON-RPC batch.
- Protocol version negotiation now returns this server's supported version (`2025-03-26`) and requires the client to send a protocol version.
- Resource templates are exposed through `resources/templates/list`, and per-session subscriptions are supported through `resources/subscribe` and `resources/unsubscribe`.
- Session-aware HTTP transport is supported with `Mcp-Session-Id`, `GET /mcp` for SSE, `POST /mcp` for JSON-RPC, and `DELETE /mcp` for explicit session teardown.
- Roots remain a client capability in MCP. This server can consume roots only if the transport/client layer later adds outbound client requests, but there is no inbound `roots/list` method for the server to expose.
- Logging support is limited to `logging/setLevel` and SSE `notifications/message`. The plain JSON response path remains request-response only.

## VS Code MCP Configuration

Use your global VS Code `mcp.json` and add a server entry named `portfolio` with your personal key:

```json
{
  "servers": {
    "portfolio": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "x-mcp-api-key": "pmcp_your_prefix.your_secret"
      }
    }
  }
}
```

On macOS with VS Code Insiders, that file is typically at `/Users/<you>/Library/Application Support/Code - Insiders/User/mcp.json`.

Start the backend before using the server from VS Code:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Authenticated portfolio tools should use a per-user MCP API key created from `/api/v1/users/me/mcp-api-keys`. The older `MCP_API_KEYS_JSON` environment variable still works for shared service access, but it is no longer the recommended path for user-scoped portfolio access.

### Local Virtualenv Recommendation

If your existing project `.venv` works, keep using it. This repo also includes a fallback local interpreter outside the OneDrive-backed project folder:

```json
{
  "python.defaultInterpreterPath": "${env:HOME}/.venvs/portfolio-manager/bin/python",
  "python.terminal.activateEnvironment": true
}
```

In this workspace, the project `.venv` exists but may hang in some synced-folder scenarios during imports or test collection. `~/.venvs/portfolio-manager` is the fallback when that happens.

You can recreate that environment with:

```bash
chmod +x setup_local_venv.sh
./setup_local_venv.sh
```

Otherwise you can continue using the existing project env, for example:

```bash
cd backend
../.venv/bin/python -m uvicorn main:app --reload --port 8000
```

## Registration Examples

### Generic HTTP MCP clients

Point the client at:

```text
http://127.0.0.1:8000/mcp
```

Use either:

- `Authorization: Bearer <access_token>` for user-scoped tools and resources.
- `x-mcp-api-key: <api_key>` for scoped service access.

If you want user-scoped portfolio tools over API key auth, prefer a DB-backed user key created from the profile endpoint. `MCP_API_KEYS_JSON` remains available for shared service integrations and local development.

### Claude Desktop or other MCP-capable clients

If the client supports remote HTTP MCP servers, register the endpoint URL and add the bearer token header. Example conceptual config:

```json
{
  "mcpServers": {
    "portfolio-manager": {
      "transport": "http",
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "Authorization": "Bearer <access-token>"
      }
    }
  }
}
```

### IDE clients

For IDE clients that support remote MCP over HTTP, use the same URL and header strategy. If the IDE only supports local stdio servers, add a thin launcher later or front this server with a small bridge process.

## Example Requests

### Initialize

```bash
curl -s http://127.0.0.1:8000/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "clientInfo": {"name": "curl-demo", "version": "1.0.0"}
    }
  }'
```

### Discover tools

```bash
curl -s http://127.0.0.1:8000/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}'
```

### Call a public tool

```bash
curl -s http://127.0.0.1:8000/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "exchange.convert",
      "arguments": {"amount": 100, "from_currency": "USD", "to_currency": "CAD"}
    }
  }'
```

### Read a public resource

```bash
curl -s http://127.0.0.1:8000/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "resources/read",
    "params": {"uri": "system://health"}
  }'
```

### Get a prompt template

```bash
curl -s http://127.0.0.1:8000/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "prompts/get",
    "params": {
      "name": "portfolio.analysis.summary",
      "arguments": {"question": "Summarize risk and concentration.", "currency": "USD"}
    }
  }'
```

## Example MCP Apps Response

`portfolio.get_summary` returns standard MCP content plus Apps UI metadata:

```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Portfolio My Portfolio is worth 152430.14 USD across 12 holdings."
      }
    ],
    "structuredContent": {
      "id": 1,
      "name": "My Portfolio",
      "total_value": 152430.14,
      "currency": "USD"
    },
    "_meta": {
      "ui": {
        "resourceUri": "ui://portfolio/dashboard/current",
        "type": "dashboard",
        "schema": {
          "title": "Portfolio overview",
          "cards": [
            {"key": "total_value", "label": "Total value", "format": "currency"},
            {"key": "total_return_percentage", "label": "Return %", "format": "percentage"}
          ]
        },
        "data": {
          "id": 1,
          "name": "My Portfolio",
          "total_value": 152430.14,
          "currency": "USD"
        }
      }
    }
  }
}
```

The same pattern is used for:

- `holdings.open_create_form` with a form schema.
- `portfolio.rebalance_workflow` with a multi-step workflow schema.

## Sample Client Script

Run the demo client:

```bash
cd backend
python scripts/mcp_client_demo.py --base-url http://127.0.0.1:8000/mcp
```

Add `--token <access-token>` to exercise authenticated tools.

## Initial Capability Set

### Tools

- `portfolio.get_summary`
- `portfolio.get_analysis`
- `holdings.list`
- `holdings.create`
- `holdings.open_create_form`
- `market.get_quote`
- `exchange.convert`
- `portfolio.refresh_metrics`
- `portfolio.rebalance_workflow`

### Resources

- `system://health`
- `portfolio://current/summary`
- `portfolio://current/holdings`
- `market://quote/{symbol}`

### Prompts

- `portfolio.analysis.summary`
- `portfolio.rebalance.suggestion`
- `portfolio.onboarding.import_guidance`

## Notes

- The server is embedded in the existing FastAPI backend and reuses the current auth and domain logic.
- Read operations degrade cleanly for non-Apps clients because the `_meta.ui` block is optional metadata.
- The initial SSE support is response streaming over the same `/mcp` endpoint when the client requests `text/event-stream`.
- For clients that need stdio transport, add a separate bridge process later rather than duplicating the business logic.