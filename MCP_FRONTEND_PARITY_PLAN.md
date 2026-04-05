# MCP Frontend Parity Plan

## Goal

Expose the meaningful interactive surface of the portfolio dashboard through the MCP server so an MCP client can perform the same core jobs as the web app:

- inspect portfolio state
- navigate major workflows
- create and update holdings
- manage cash
- run analytics
- inspect market data
- perform onboarding/import flows
- manage MCP access keys

This is parity for portfolio operations and analytical workflows, not a literal reproduction of every React interaction.

## Current State

The current MCP server already covers a useful backend subset:

- tools:
  - `portfolio_get_summary`
  - `portfolio_get_analysis`
  - `holdings_list`
  - `holdings_create`
  - `holdings_open_create_form`
  - `market_get_quote`
  - `exchange_convert`
  - `portfolio_refresh_metrics`
  - `portfolio_rebalance_workflow`
- resources:
  - `system://health`
  - `portfolio://current/summary`
  - `portfolio://current/holdings`
  - `market://quote/{symbol}`
- prompts:
  - `portfolio.analysis.summary`
  - `portfolio.rebalance.suggestion`
  - `portfolio.onboarding.import_guidance`

That original baseline has now been extended. The MCP server now covers the protected-route surface for overview, portfolio management, analytics tabs, live market, settings, and onboarding flows. The remaining work, if any, should be treated as refinement inside existing capabilities rather than missing route parity.

## Route Map

Primary protected routes from `frontend/src/App.jsx`:

- `/dashboard/overview`
- `/dashboard/portfolio`
- `/dashboard/analytics`
- `/dashboard/settings`
- `/dashboard/live-market`
- `/dashboard/update-portfolio`
- `/onboarding`

Public auth routes exist, but they should remain outside MCP scope. MCP should rely on the existing per-user API key model rather than reproducing login/register UI.

## Parity Matrix

### Overview

Frontend surface:

- page: `frontend/src/pages/Overview.jsx`
- data source: `frontend/src/components/OverviewSection.jsx`
- user job: inspect summary metrics, performance metrics, and per-asset performance distribution

Current MCP coverage:

- partial via `portfolio_get_summary`
- partial via `portfolio_get_analysis`

Gap:

- no single overview payload matching the dashboard composition
- no dedicated resource for overview metrics history/distribution

Recommended MCP additions:

- tool: `overview_get_dashboard`
- resource: `portfolio://current/overview`
- resource: `portfolio://current/performance-distribution`
- prompt: `portfolio.overview.explain_metric`

Apps output:

- dashboard card set for top-level KPIs
- chart/table metadata for performance distribution

Status:

- implemented with `overview_get_dashboard`
- implemented with `overview://dashboard/current`

### Portfolio

Frontend surface:

- page: `frontend/src/pages/Portfolio.jsx`
- components include cash balance, allocation, performance view, transaction history
- user jobs:
  - inspect holdings and allocation
  - inspect cash balance
  - inspect transaction history

Current MCP coverage:

- partial via `holdings_list`
- partial via `portfolio://current/holdings`
- partial via `portfolio://current/summary`

Gap:

- no transaction history exposure
- no dedicated cash balance tool/resource
- no portfolio page aggregate payload
- no allocation-specific or performance-specific resources

Recommended MCP additions:

- tool: `portfolio_get_page`
- tool: `portfolio_get_cash_balance`
- tool: `transactions_list`
- resource: `portfolio://current/cash-balance`
- resource: `portfolio://current/transactions`
- resource: `portfolio://current/allocation`
- resource: `portfolio://current/performance-metrics`

Apps output:

- table UI for transactions
- dashboard UI for cash and allocation

### Analytics

Frontend surface:

- page: `frontend/src/pages/Analytics.jsx`
- tabs:
  - risk
  - allocation
  - efficient frontier
  - monte carlo
  - cppi
- user jobs:
  - switch analytical views
  - retrieve model outputs for each strategy/analysis type

Current MCP coverage:

- partial via `portfolio_get_analysis`
- partial via `portfolio_rebalance_workflow`

Gap:

- analytics are not split into tab-level capabilities
- no tool/resources dedicated to efficient frontier, monte carlo, or CPPI
- no workflow state for view selection or parameterized analysis requests

Recommended MCP additions:

- tool: `analytics_get_risk`
- tool: `analytics_get_allocation`
- tool: `analytics_get_efficient_frontier`
- tool: `analytics_get_monte_carlo`
- tool: `analytics_get_cppi`
- resource: `analytics://risk/current`
- resource: `analytics://allocation/current`
- resource: `analytics://efficient-frontier/current`
- resource: `analytics://monte-carlo/current`
- resource: `analytics://cppi/current`
- prompt: `analytics.explain_results`

Apps output:

- dashboard or chart metadata per tab
- workflow for parameterized runs where the analysis accepts constraints or assumptions

Status:

- implemented with tab-level analytics tools and resources for risk, allocation, efficient frontier, Monte Carlo, and CPPI

### Live Market

Frontend surface:

- page: `frontend/src/pages/LiveMarket.jsx`
- user jobs:
  - inspect live quotes for owned positions
  - search/filter holdings
  - sort data
  - receive near-real-time updates over websocket

Current MCP coverage:

- partial via `market_get_quote`
- partial via `market://quote/{symbol}`

Gap:

- no portfolio-level live market snapshot
- no watchlist or holdings market board
- no streaming market update resource or subscription surface
- no search/sort semantics at the MCP layer

Recommended MCP additions:

- tool: `market_get_live_board`
- tool: `market_search_symbols`
- resource: `market://portfolio/live-board`
- resource: `market://portfolio/live-board/{sort_key}`
- resource: `market://history/{symbol}`
- subscription target: `market://portfolio/live-board`
- subscription target: `market://quote/{symbol}`

Apps output:

- table UI for market board
- chart UI for selected ticker history

Implementation note:

- this is the clearest place to use resource subscriptions and `notifications/resources/updated`

Status:

- implemented for `market_get_live_board` and `market://portfolio/live-board`

### Update Portfolio

Frontend surface:

- page: `frontend/src/pages/UpdatePortfolio.jsx`
- forms:
  - `BuyAssetForm`
  - `SellAssetForm`
  - `EditAssetForm`
  - `AddCashFormInline`
- user jobs:
  - buy assets
  - sell assets
  - edit holdings
  - deposit cash
  - withdraw cash

Current MCP coverage:

- partial via `holdings_create`
- partial via `holdings_open_create_form`

Gap:

- no sell flow
- no edit holding flow
- no cash deposit/withdraw flow
- no multi-step portfolio update workflow
- no generated forms for sell/edit/cash actions

Recommended MCP additions:

- tool: `holdings_open_sell_form`
- tool: `holdings_open_edit_form`
- tool: `cash_open_transaction_form`
- tool: `holdings_sell`
- tool: `holdings_update`
- tool: `cash_deposit`
- tool: `cash_withdraw`
- tool: `portfolio_update_workflow`
- resource: `portfolio://current/holdings/{holding_id}`

Apps output:

- form UI for each action

Status:

- implemented
- workflow UI for end-to-end portfolio update tasks

### Onboarding

Frontend surface:

- page: `frontend/src/pages/Onboarding.jsx`
- component: `frontend/src/components/onboarding/PortfolioOnboarding.jsx`
- user jobs:
  - choose manual or CSV upload
  - add multiple assets
  - import broker-style CSV
  - complete onboarding and transition into dashboard

Current MCP coverage:

- partial via `portfolio.onboarding.import_guidance`

Gap:

- no onboarding form schema
- no CSV import workflow
- no import preview/validation step
- no onboarding completion workflow state

Recommended MCP additions:

- tool: `onboarding_open_manual_form`
- tool: `onboarding_open_csv_import_form`
- tool: `onboarding_validate_csv_import`
- tool: `onboarding_import_assets`
- tool: `onboarding_complete`
- workflow: `onboarding_import_workflow`
- resource: `portfolio://current/onboarding-status`

Apps output:

- form UI for manual multi-row asset entry
- workflow UI for CSV upload, validation, preview, and commit

### Settings

Frontend surface:

- page: `frontend/src/pages/Settings.jsx`
- user jobs:
  - list existing MCP API keys
  - create key
  - rotate key
  - revoke key
  - copy newly revealed key

Current MCP coverage:

- none through MCP itself
- REST endpoints exist and are already used by the web app

Gap:

- no MCP key-management surface through the MCP server

Recommended MCP additions:

- tool: `settings_list_mcp_api_keys`
- tool: `settings_open_create_mcp_api_key_form`
- tool: `settings_create_mcp_api_key`
- tool: `settings_rotate_mcp_api_key`
- tool: `settings_revoke_mcp_api_key`
- resource: `settings://mcp-api-keys`

Apps output:

- table UI for keys
- form UI for key creation and rotation

Security note:

- returning a newly created raw key through MCP is acceptable only if that response is explicitly single-view and marked sensitive in `_meta`

## Capability Model

Use the following modeling rules to keep the MCP surface coherent:

- tools:
  - mutations
  - workflow transitions
  - explicit server actions
- resources:
  - stable read models
  - stream/subscription targets
  - entity views and filtered board views
- prompts:
  - explanatory wrappers around analysis and onboarding
  - user-facing reasoning templates, not CRUD
- Apps metadata:
  - `dashboard` for summaries and KPI panels
  - `table` for holdings, transactions, keys, and live market lists
  - `form` for create/edit/sell/cash/onboarding steps
  - `workflow` for onboarding, rebalance, and portfolio update flows

## Recommended Phases

### Phase 1: Page Read Models

Ship read parity first:

- `overview_get_dashboard`
- `portfolio_get_page`
- `portfolio_get_cash_balance`
- `transactions_list`
- analytics tab-specific read tools/resources
- `market_get_live_board`

Success condition:

- an MCP client can inspect the same primary data shown on Overview, Portfolio, Analytics, and Live Market without using the web app

### Phase 2: Mutation Parity

Ship portfolio update actions:

- `holdings_sell`
- `holdings_update`
- `cash_deposit`
- `cash_withdraw`
- corresponding form tools

Success condition:

- an MCP client can complete the full Update Portfolio page jobs end to end

### Phase 3: Onboarding and Import

Ship onboarding workflow:

- manual form
- CSV form
- import validation preview
- import commit
- onboarding completion state

Success condition:

- first-time portfolio creation and subsequent CSV imports work fully through MCP

### Phase 4: Settings and Access Management

Ship settings parity:

- list/create/rotate/revoke MCP API keys

Success condition:

- the Settings page's MCP access section is fully usable through MCP

### Phase 5: Live Interactivity and Notifications

Ship streaming/resource updates:

- live market board subscriptions
- holdings/summary/transaction update notifications
- richer progress updates for longer-running analytics or imports

Success condition:

- MCP clients receive timely updates instead of polling for every portfolio state change

## Highest-Value Additions

If parity work needs to be prioritized hard, build these first:

1. `holdings_sell`
2. `holdings_update`
3. `cash_deposit`
4. `cash_withdraw`
5. `transactions_list`
6. `market_get_live_board`
7. `onboarding_import_assets`
8. `settings_list_mcp_api_keys`

Those close the biggest user-visible gaps relative to the current dashboard.

## Non-Goals

The MCP server does not need to reproduce browser-only mechanics such as:

- route transitions
- tab highlight state
- search box focus behavior
- exact React component trees
- toast animation behavior

The correct target is task parity and structured interactive outputs, not HTML parity.

## Definition of Done

Frontend parity is achieved when:

- every protected route has a corresponding MCP read surface
- every protected route with mutations has MCP tools for those mutations
- the most important forms can be rendered through MCP Apps metadata
- long-running or real-time flows use resources plus subscriptions instead of ad hoc polling
- the MCP README documents the new route-to-capability mapping
