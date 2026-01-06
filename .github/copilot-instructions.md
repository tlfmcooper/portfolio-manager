# Portfolio Dashboard - AI Coding Agent Instructions

## Architecture Overview

Full-stack investment portfolio management app with **FastAPI async backend** and **React + Vite frontend**.

```
backend/app/
├── api/v1/          # REST endpoints (auth, portfolios, holdings, analysis)
├── core/            # Config, database, security, redis
├── crud/            # Database operations (async SQLAlchemy)
├── models/          # SQLAlchemy ORM models (User, Portfolio, Holding, Asset, Transaction)
├── schemas/         # Pydantic request/response schemas
├── services/        # Business logic (portfolio_analysis, finnhub_service, exchange_rate_service)
└── utils/           # Dependencies, helpers

frontend/src/
├── components/      # React components (charts, forms, UI primitives)
├── contexts/        # React contexts (AuthContext, ThemeContext, CurrencyContext, AgentContext)
├── pages/           # Route components (Dashboard, Portfolio, Analytics, LiveMarket)
├── services/        # API services with offline fallback (portfolioService, offlineStorage)
└── utils/           # API config, helpers
```

## Critical Patterns

### Backend: Always Async
All database and API operations use `async/await`. Never use synchronous patterns.

```python
# ✅ Correct
@router.get("/portfolios")
async def get_portfolio(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    portfolio = await get_user_portfolio(db, current_user.id)

# ❌ Wrong - synchronous
def get_portfolio(db: Session = Depends(get_db)):
```

### Backend: Authentication Dependencies
Use dependency injection for auth. Three levels exist:
- `get_current_user` - Any authenticated user
- `get_current_active_user` - Active account required
- `get_current_superuser` - Admin privileges required

### Frontend: Context Provider Hierarchy
Order matters - contexts are nested in `App.jsx`:
```jsx
<ThemeProvider>
  <AuthProvider>      {/* Provides api, user, portfolioId */}
    <CurrencyProvider>
      <AgentProvider>
```

### Frontend: API Calls Pattern
Use the `api` instance from `useAuth()` hook - it has auth token interceptors:
```jsx
const { api } = useAuth();
const response = await api.get('/portfolios/summary');
```

For offline support, use `PortfolioService` from `services/portfolioService.js` which wraps API calls with IndexedDB caching.

## Database Models & Relationships

```
User 1:1 Portfolio 1:N Holding N:1 Asset
                   1:N Transaction
```

Key constraint: `(portfolio_id, ticker)` is unique on `holdings` table.

## Environment Variables

**Backend (.env):**
- `DATABASE_URL` - PostgreSQL connection (auto-converts to asyncpg)
- `SECRET_KEY` - JWT signing key
- `FINNHUB_API_KEY` - Stock quotes API
- `EXCHANGE_RATES_API_KEY` - Currency conversion
- `REDIS_URL` - Caching (optional)

**Frontend (.env):**
- `VITE_API_URL` - Backend API base URL (auto-detects localhost in dev)
- `VITE_GEMINI_API_KEY` - AI chatbot integration

## Development Commands

```bash
# Backend (from backend/)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (from frontend/)
npm install
npm run dev          # Dev server on :5173
npm run build        # Production build
npm test             # Vitest tests

# Full stack via Podman/Docker
podman-compose up -d
```

## Testing Patterns

**Backend:** `pytest-asyncio` for async tests
```python
@pytest.mark.asyncio
async def test_get_portfolio(async_client):
    response = await async_client.get("/api/v1/portfolios/")
```

**Frontend:** Vitest + React Testing Library
```javascript
// Tests in frontend/tests/unit/ and frontend/tests/integration/
import { render, screen } from '@testing-library/react';
```

## Styling Conventions

Tailwind CSS with CSS custom properties for theming:
- Theme variables defined in `frontend/src/index.css` (e.g., `--color-primary`, `--color-background`)
- Dark mode via `.dark` class on `<html>` element
- Use `style={{ color: 'var(--color-text)' }}` for theme-aware inline styles

## API Endpoint Structure

All endpoints prefixed with `/api/v1/`:
- `POST /auth/login` - OAuth2 form login (username, password)
- `POST /auth/register` - User registration
- `GET /portfolios/` - Get user's portfolio
- `GET /portfolios/summary` - Portfolio with metrics
- `GET /portfolios/analysis?currency=USD` - Full analytics
- `GET /holdings/` - Paginated holdings list
- `GET /market/quote/{symbol}` - Live stock quote

## Common Gotchas

1. **Currency param:** Many endpoints accept `?currency=USD` or `?currency=CAD` for conversion
2. **Paginated responses:** Holdings API returns `{ items: [], total: n }` structure
3. **Token refresh:** Access tokens expire in 30 min; refresh tokens in 7 days
4. **yfinance fallback:** When market data fails, mock data is returned gracefully
5. **Onboarding flow:** New users without a portfolio are routed to `/onboarding`

## File Naming Conventions

- Backend: `snake_case.py` for modules
- Frontend: `PascalCase.jsx` for components, `camelCase.js` for utilities
- Schemas: Match model names (e.g., `PortfolioInDB`, `PortfolioUpdate`, `PortfolioSummary`)
