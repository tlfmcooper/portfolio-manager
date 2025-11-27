# CLAUDE.MD - Portfolio Dashboard Project Guide

## Project Overview

This is a full-stack **Advanced Portfolio Management Dashboard** that provides professional-grade financial analytics, risk management, and portfolio optimization tools. The application enables users to track investment portfolios with real-time market data, advanced analytics, and interactive visualizations.

**Key Capabilities:**
- Real-time market data integration via Yahoo Finance
- Advanced portfolio analytics (Sharpe ratio, VaR, efficient frontier, Monte Carlo simulations)
- Multi-user authentication and authorization system
- CPPI (Constant Proportion Portfolio Insurance) strategy analysis
- Comprehensive risk management and performance tracking
- Progressive Web App (PWA) with offline support

## Tech Stack

### Backend
- **Framework:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL with SQLAlchemy async ORM
- **Caching:** Redis for session management and data caching
- **Authentication:** JWT tokens with bcrypt password hashing
- **Data Sources:** yfinance for real-time market data
- **Analytics:** NumPy, Pandas, SciPy for financial calculations
- **Deployment:** Uvicorn ASGI server

### Frontend
- **Framework:** React 18 with Vite
- **Styling:** Tailwind CSS with dark mode support
- **Charts:** Recharts for interactive visualizations
- **State Management:** React hooks and context
- **HTTP Client:** Axios
- **Icons:** Lucide React
- **PWA:** vite-plugin-pwa with Workbox
- **AI Integration:** Google Generative AI for chatbot features

## Project Structure

```
portfolio-dashboard/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   │   ├── analysis.py  # Portfolio analytics endpoints
│   │   │   ├── assets.py    # Asset management
│   │   │   ├── auth.py      # Authentication endpoints
│   │   │   ├── exchange.py  # Currency exchange rates
│   │   │   ├── holdings.py  # Portfolio holdings CRUD
│   │   │   ├── portfolios.py # Portfolio management
│   │   │   └── users.py     # User management
│   │   ├── core/            # Core configuration
│   │   │   ├── config.py    # Settings & environment vars
│   │   │   ├── database.py  # Database setup
│   │   │   ├── redis_client.py # Redis configuration
│   │   │   └── security.py  # JWT & password hashing
│   │   ├── crud/            # Database operations
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── utils/           # Utility functions
│   ├── main.py              # Application entry point
│   └── requirements.txt     # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── utils/           # Utility functions
│   │   ├── App.jsx          # Main app component
│   │   └── main.jsx         # Application entry point
│   ├── public/              # Static assets
│   ├── package.json         # Node dependencies
│   └── vite.config.js       # Vite configuration
│
├── .claude/                 # Claude Code configuration
├── .github/workflows/       # CI/CD pipelines
├── specs/                   # Project specifications
├── README.md                # User documentation
└── CLAUDE.MD                # This file (AI assistant guide)
```

## Key Files & Their Purposes

### Backend Core Files
- `backend/main.py:36-42` - Application lifespan management and database initialization
- `backend/app/core/config.py` - Environment configuration and settings (uses Pydantic BaseSettings)
- `backend/app/core/database.py` - Async SQLAlchemy engine and session management
- `backend/app/core/security.py` - JWT token creation/verification, password hashing
- `backend/app/api/v1/auth.py` - Login, registration, and token refresh endpoints
- `backend/app/api/v1/analysis.py` - Portfolio analytics (efficient frontier, Monte Carlo, CPPI)
- `backend/app/api/v1/portfolios.py` - Portfolio CRUD operations and summary calculations

### Frontend Core Files
- `frontend/src/App.jsx` - Main app with routing and authentication context
- `frontend/src/pages/Dashboard.jsx` - Main dashboard with portfolio overview
- `frontend/src/pages/Analysis.jsx` - Advanced analytics visualizations
- `frontend/src/components/ChatWidget.jsx` - AI chatbot integration
- `frontend/src/utils/api.js` - Axios instance with auth interceptors

## Important Patterns & Conventions

### Backend Patterns

1. **Async/Await Throughout**
   - All database operations use `async`/`await`
   - FastAPI endpoints are async functions
   - Use `AsyncSession` for database access

2. **Dependency Injection**
   ```python
   @router.get("/portfolios")
   async def get_portfolios(
       db: AsyncSession = Depends(get_db),
       current_user: User = Depends(get_current_user)
   ):
       # Implementation
   ```

3. **Error Handling**
   - Use FastAPI's `HTTPException` with appropriate status codes
   - Implement try-except blocks for external API calls (yfinance)
   - Graceful fallback to mock/cached data when external services fail

4. **Authentication Flow**
   - JWT access tokens (30 min expiry)
   - JWT refresh tokens (7 day expiry)
   - Tokens stored in HTTP-only cookies (production) or localStorage (dev)
   - Protected routes use `Depends(get_current_user)` or `Depends(get_current_superuser)`

### Frontend Patterns

1. **Component Structure**
   - Functional components with hooks
   - Custom hooks for shared logic (e.g., `useAuth`, `useDarkMode`)
   - Props destructuring for clarity

2. **API Calls**
   - Centralized API client in `utils/api.js`
   - Automatic token injection via Axios interceptors
   - Error handling with toast notifications

3. **State Management**
   - React Context for global state (auth, theme)
   - Local component state with `useState`
   - `useEffect` for data fetching

4. **Styling**
   - Tailwind utility classes
   - Dark mode: `dark:` prefix classes
   - Responsive: `sm:`, `md:`, `lg:`, `xl:` prefixes

## Environment Variables

### Backend (.env)
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/portfolio_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:5173","https://yourdomain.com"]

# Debug
DEBUG=true
```

### Frontend (.env)
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_GEMINI_API_KEY=your-gemini-api-key
```

## Development Workflow

### Starting the Development Environment

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Using Docker:**
```bash
docker-compose up -d
```

### Running Tests

**Backend:**
```bash
cd backend
pytest tests/ -v
```

**Frontend:**
```bash
cd frontend
npm test
```

### Database Migrations

The project uses SQLAlchemy models with automatic table creation on startup via `create_tables()` in `main.py:39`.

For production, consider implementing Alembic migrations:
```bash
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Common Tasks & How to Do Them

### Adding a New API Endpoint

1. Create endpoint in appropriate router (e.g., `backend/app/api/v1/portfolios.py`)
2. Define Pydantic schema in `backend/app/schemas/`
3. Implement CRUD operation in `backend/app/crud/`
4. Add authentication dependency if needed
5. Update frontend API client in `frontend/src/utils/api.js`

### Adding a New Page/Route

1. Create component in `frontend/src/pages/`
2. Add route in `frontend/src/App.jsx`
3. Create navigation link in sidebar/header component
4. Implement authentication guard if needed

### Adding a New Database Model

1. Create model in `backend/app/models/`
2. Define schema in `backend/app/schemas/`
3. Create CRUD operations in `backend/app/crud/`
4. Restart server to auto-create tables (or run migration)

### Integrating New Financial Analytics

1. Implement calculation logic in `backend/app/utils/` or create new service
2. Add endpoint in `backend/app/api/v1/analysis.py`
3. Create visualization component in `frontend/src/components/`
4. Add to appropriate dashboard section

## Debugging Tips

### Backend Debugging

1. **Check API docs:** `http://localhost:8000/docs`
2. **Enable SQL logging:** Set `echo=True` in database engine creation
3. **Use FastAPI's built-in validation errors** - Pydantic provides detailed error messages
4. **Check Redis connection:** Ensure Redis is running for caching features

### Frontend Debugging

1. **React DevTools:** Install browser extension for component inspection
2. **Network tab:** Monitor API calls and responses
3. **Console errors:** Check browser console for JavaScript errors
4. **Tailwind IntelliSense:** Use VS Code extension for class suggestions

## Security Considerations

1. **Never commit secrets** - Use `.env` files (already in `.gitignore`)
2. **Password hashing** - Uses bcrypt via `passlib`
3. **SQL injection protection** - SQLAlchemy ORM handles parameterization
4. **CORS configuration** - Properly configured in `main.py:86-92`
5. **JWT token expiry** - Tokens expire after 30 minutes
6. **Input validation** - Pydantic schemas validate all input data

## Performance Optimization

1. **Database Queries:**
   - Use `selectinload()` or `joinedload()` for eager loading relationships
   - Implement pagination for large result sets
   - Add database indexes on frequently queried columns

2. **Caching:**
   - Redis caching for market data (reduces API calls)
   - Frontend caching via service workers (PWA)

3. **Frontend:**
   - Lazy loading for route components
   - Memoization for expensive calculations
   - Debouncing for search inputs

## Deployment

### Railway Deployment (Current Setup)

The project is configured for Railway deployment with:
- `backend/railway.json` - Railway backend configuration
- `frontend/railway.json` - Railway frontend configuration
- Environment variables set in Railway dashboard

### Alternative Deployment Options

**Docker:**
```bash
docker-compose -f docker-compose.yml up -d
```

**Manual Deployment:**
1. Set up PostgreSQL and Redis servers
2. Configure environment variables
3. Run database migrations
4. Build frontend: `npm run build`
5. Serve backend with Gunicorn + Uvicorn workers
6. Serve frontend with Nginx

## Testing Strategy

### Backend Tests
- Unit tests for CRUD operations
- Integration tests for API endpoints
- Test authentication flows
- Mock external API calls (yfinance)

### Frontend Tests
- Component rendering tests
- User interaction tests (React Testing Library)
- API integration tests with mock server

## Troubleshooting Common Issues

### Issue: Backend won't start
- Check Python version (requires 3.11+)
- Verify PostgreSQL is running
- Check DATABASE_URL in .env
- Ensure all dependencies installed: `pip install -r requirements.txt`

### Issue: Frontend build fails
- Clear node_modules: `rm -rf node_modules && npm install`
- Check Node.js version (requires 18+)
- Verify all environment variables set

### Issue: Market data not loading
- Check internet connection
- Verify yfinance package installed
- Check for API rate limiting
- Fallback to mock data may be active

### Issue: Authentication not working
- Verify SECRET_KEY is set in backend .env
- Check token expiry settings
- Clear browser localStorage/cookies
- Check CORS configuration

## Recent Changes & Features

Based on recent git commits:
- Improved chatbot UI (commit: 394bde9)
- Enhanced mobile performance (commit: d2a9c59)
- Fixed sidebar closing bug on mobile (commits: 4bdcfb3, 51aafbc)
- Added API configuration improvements (commit: 9859025)

## Future Roadmap

See `README.md:345-358` for planned features:
- Real-time WebSocket updates
- Advanced backtesting engine
- Custom benchmark comparisons
- Alert system for portfolio events
- PDF report generation
- Multi-currency support
- Options and derivatives analysis
- ESG scoring integration

## Resources & Documentation

- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **React Docs:** https://react.dev/
- **SQLAlchemy Async:** https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html
- **Recharts:** https://recharts.org/
- **Tailwind CSS:** https://tailwindcss.com/

## Getting Help

- Check API documentation: `http://localhost:8000/docs`
- Review troubleshooting section in `README.md:315-343`
- Check GitHub issues for similar problems
- Review recent commits for context on changes

---

**Note for AI Assistants:** This project uses modern async patterns throughout. Always use async/await for database operations, respect the authentication system, and maintain the existing code style and patterns. When adding new features, follow the established project structure and conventions.
