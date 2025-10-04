# AI-Powered Portfolio Chat Assistant

## Overview

This feature adds an intelligent AI chat assistant to the Portfolio Manager application, enabling users to interact with their portfolio analytics through natural language conversations. The assistant leverages Claude AI with Model Context Protocol (MCP) integration to provide real-time portfolio analysis, rebalancing simulations, and comprehensive financial guidance.

## Architecture

### Backend (FastAPI)

```
backend/
├── app/
│   ├── api/v1/
│   │   ├── auth.py          # JWT authentication endpoints
│   │   ├── portfolios.py    # Portfolio CRUD and metrics
│   │   └── chat.py          # Chat sessions and SSE streaming
│   ├── core/
│   │   ├── config.py        # Application configuration
│   │   ├── security.py      # JWT and password hashing
│   │   └── redis_client.py  # Redis caching client
│   ├── models/
│   │   ├── database.py      # SQLAlchemy setup
│   │   ├── user.py          # User model
│   │   └── portfolio.py     # Portfolio and Holding models
│   ├── schemas/
│   │   ├── auth.py          # Authentication schemas
│   │   ├── portfolio.py     # Portfolio schemas
│   │   └── chat.py          # Chat schemas
│   ├── services/
│   │   ├── portfolio_analysis.py  # Wrapper for portfolio_manager library
│   │   ├── mcp_server.py          # MCP tools for Claude
│   │   └── chat_service.py        # Chat orchestration with SSE
│   └── main.py              # FastAPI application entry point
└── requirements.txt
```

### Frontend (React)

```
frontend/
├── src/
│   ├── components/
│   │   ├── Layout.js           # Main app layout with sidebar
│   │   ├── PrivateRoute.js     # Authentication wrapper
│   │   ├── ChatMessage.js      # Individual message display
│   │   ├── ChatInput.js        # Message input with streaming
│   │   └── DashboardPreview.js # Inline analytics visualization
│   ├── contexts/
│   │   └── AuthContext.js      # Authentication state
│   ├── hooks/
│   │   └── useChat.js          # SSE streaming logic
│   ├── pages/
│   │   ├── Login.js            # Login page
│   │   ├── Register.js         # Registration page
│   │   ├── Dashboard.js        # Main dashboard
│   │   ├── Portfolios.js       # Portfolio management
│   │   └── Chat.js             # AI chat interface
│   ├── services/
│   │   └── api.js              # API client
│   ├── App.js                  # Main app component
│   └── index.js                # Entry point
└── package.json
```

## Features

### 1. MCP Tools (Portfolio Analytics)

The assistant has access to 7 powerful MCP tools:

#### `get_portfolio_summary`
Returns comprehensive portfolio metrics:
- Total return
- Annualized return
- Volatility
- Sharpe ratio
- Sortino ratio
- Maximum drawdown
- VaR (95%)
- CVaR (95%)

#### `calculate_portfolio_metrics`
Same as `get_portfolio_summary` (alias for consistency)

#### `get_risk_metrics`
Detailed risk analysis:
- VaR at 95% and 99% confidence
- CVaR (Expected Shortfall)
- Volatility (annualized)
- Maximum drawdown
- Correlation matrix

#### `simulate_rebalancing`
Simulates portfolio changes:
- Input: `{"AAPL": -10, "QBTS": 50}` (percentage changes)
- Returns: Before/after comparison of all metrics
- Automatically normalizes allocations to 100%

#### `run_efficient_frontier`
Generates optimal portfolios:
- 100 portfolios on the efficient frontier
- Current portfolio position
- Maximum Sharpe ratio portfolio
- Minimum volatility portfolio

#### `run_monte_carlo`
Stochastic simulation:
- Default: 1000 scenarios over 252 days (1 year)
- Returns distribution statistics
- Percentiles (5th, 25th, 75th, 95th)
- Probability of positive returns

#### `run_cppi_simulation`
CPPI strategy simulation:
- Dynamic risk management
- Configurable multiplier and floor
- Tracks portfolio value over time
- Shows maximum drawdown

### 2. Chat Interface

**Key Components:**

- **ChatMessage**: Displays user and assistant messages with avatars
- **ChatInput**: Multi-line input with keyboard shortcuts (Enter to send, Shift+Enter for new line)
- **DashboardPreview**: Inline visualization of analytics results with charts
- **useChat hook**: Manages SSE streaming, message state, and error handling

**Features:**
- Real-time streaming responses
- Message history persistence (30 days in Redis)
- Tool call notifications
- Inline dashboard updates
- Error handling and recovery
- Stop streaming capability

### 3. Authentication System

**JWT-based authentication:**
- User registration with email/username/password
- Login with access token (30-minute expiry)
- Protected routes requiring authentication
- Token stored in localStorage
- Automatic token injection in API requests

**Endpoints:**
- `POST /api/v1/auth/register` - Create new user
- `POST /api/v1/auth/login` - Login and get token
- `GET /api/v1/auth/me` - Get current user info

### 4. Portfolio Management

**Endpoints:**
- `POST /api/v1/portfolios` - Create portfolio
- `GET /api/v1/portfolios` - List user's portfolios
- `GET /api/v1/portfolios/{id}` - Get portfolio details
- `PUT /api/v1/portfolios/{id}` - Update portfolio
- `DELETE /api/v1/portfolios/{id}` - Delete portfolio
- `GET /api/v1/portfolios/{id}/metrics` - Get performance metrics
- `GET /api/v1/portfolios/{id}/risk` - Get risk metrics

### 5. Chat Sessions

**Endpoints:**
- `POST /api/v1/chat/sessions` - Create new session
- `GET /api/v1/chat/sessions/{id}` - Get session history
- `POST /api/v1/chat/sessions/{id}/messages` - Send message (SSE stream)
- `DELETE /api/v1/chat/sessions/{id}` - Delete session

**SSE Response Format:**
```json
{
  "type": "message_delta",
  "content": "Analyzing your portfolio..."
}

{
  "type": "tool_call",
  "tool_call": {
    "name": "simulate_rebalancing",
    "status": "started"
  }
}

{
  "type": "dashboard_update",
  "dashboard_update": {
    "tool": "get_risk_metrics",
    "data": { ... }
  }
}

{
  "type": "done"
}
```

### 6. Redis Caching

**Cache Structure:**

```
chat:session:{user_id}:{session_id} (TTL: 30 days)
├── session_id
├── user_id
├── portfolio_id
├── messages[]
│   ├── role
│   ├── content
│   ├── timestamp
│   └── tool_call (optional)
├── dashboard_snapshots[]
├── created_at
└── last_activity
```

## Installation & Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- Redis 7+
- Anthropic API key

### Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and add:
# - SECRET_KEY (generate with: openssl rand -hex 32)
# - ANTHROPIC_API_KEY (from anthropic.com)

# Initialize database
python -c "from app.models.database import init_db; init_db()"

# Run server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm start
```

### Docker Setup (Recommended)

```bash
# Set Anthropic API key in .env
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# Start all services
podman-compose up -d

# Or with Docker Compose
docker-compose up -d
```

**Services:**
- Redis: `localhost:6379`
- Backend API: `localhost:8000`
- Frontend: `localhost:3000`

## Usage Examples

### Example 1: Portfolio Risk Analysis

**User:** "What are my portfolio's risk metrics?"

**Agent Actions:**
1. Calls `get_risk_metrics` MCP tool
2. Retrieves VaR, CVaR, volatility, correlation matrix
3. Displays inline dashboard with metrics

**Response:**
```
Your portfolio has the following risk characteristics:

- **95% VaR**: -$8,450 (maximum expected daily loss)
- **99% VaR**: -$12,300 (extreme scenario)
- **Volatility**: 22.3% annualized
- **Max Drawdown**: -15.7%

The correlation matrix shows AAPL and MSFT are highly correlated (0.85),
which increases concentration risk. Consider diversifying into uncorrelated assets.
```

### Example 2: Rebalancing Simulation

**User:** "What would happen if I decreased AAPL by 10% and increased QBTS by 50%?"

**Agent Actions:**
1. Parses allocation changes
2. Calls `simulate_rebalancing` with `{"AAPL": -10, "QBTS": 50}`
3. Calculates new normalized allocations
4. Compares current vs proposed metrics
5. Displays side-by-side comparison chart

**Response:**
```
Based on your proposed rebalancing:

📊 **Risk-Return Changes:**
- Expected Return: 12.1% → 14.7% (+2.6%)
- Volatility: 18.5% → 22.3% (+3.8%)
- Sharpe Ratio: 0.65 → 0.67 (+0.02)

⚠️ **Warning**: QBTS is a high-volatility quantum computing stock. This change
significantly increases your portfolio's risk exposure (+20% volatility increase).

**Recommendation**: Consider a smaller increase to QBTS (15-25%) to balance
risk and return more effectively.

Would you like to see a Monte Carlo simulation to model potential outcomes?
```

### Example 3: Monte Carlo Simulation

**User:** "Yes, run a Monte Carlo simulation with the new allocation"

**Agent Actions:**
1. Calls `run_monte_carlo` with 1000 scenarios, 252-day horizon
2. Simulates potential outcomes
3. Displays distribution statistics

**Response:**
```
Monte Carlo Simulation Results (1000 scenarios, 1 year):

📈 **Return Distribution:**
- Mean: +14.2%
- Median: +13.8%
- 5th Percentile: -8.5% (worst case scenario)
- 95th Percentile: +38.7% (best case scenario)

**Probabilities:**
- 72% chance of positive returns
- 28% chance of losses
- 5% chance of losses exceeding 8.5%

The simulation suggests this allocation has good upside potential but comes
with increased downside risk compared to your current portfolio.
```

## Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v --cov=app
```

**Test Coverage:**
- MCP tools execution
- Chat service (session management, messaging)
- Authentication
- Portfolio CRUD operations

### Frontend Tests

```bash
cd frontend
npm test
```

## Security Considerations

1. **API Key Storage**: Never commit `.env` files. Use environment variables in production.
2. **JWT Secret**: Generate a strong secret key (`openssl rand -hex 32`)
3. **CORS**: Configure `CORS_ORIGINS` to allow only trusted domains
4. **Rate Limiting**: Consider adding rate limiting for expensive MCP operations
5. **Input Validation**: All inputs are validated via Pydantic schemas

## Performance Optimization

1. **Redis Caching**:
   - Chat sessions: 30 days TTL
   - Portfolio metrics: 5-10 minutes (implement as needed)
   - Market data: 1 minute (via existing library cache)

2. **SSE Streaming**:
   - Chunks responses for real-time feedback
   - Prevents timeout on long-running analytics

3. **Database Indexing**:
   - Indexes on `user_id`, `portfolio_id`, `email`, `username`

## Known Limitations

1. **SSE Browser Support**: EventSource polyfill may be needed for older browsers
2. **Redis Dependency**: Application requires Redis for chat functionality
3. **API Key Required**: Anthropic API key needed for AI features
4. **Market Data**: Depends on Yahoo Finance API availability

## Future Enhancements

1. **Portfolio Comparison**: Compare multiple portfolios side-by-side
2. **Historical Analysis**: Time-series analysis and backtesting
3. **Custom Alerts**: Risk threshold notifications
4. **Export Reports**: PDF/Excel export of analytics
5. **Voice Input**: Speech-to-text for chat
6. **Multi-language**: Internationalization support
7. **Public Finance MCPs**: Integrate stock market data MCPs
8. **Persistent Rebalancing**: Save simulated allocations as new portfolios

## Troubleshooting

### SSE Connection Issues

**Problem**: Chat messages not streaming

**Solutions**:
- Check browser console for EventSource errors
- Verify CORS settings in backend config
- Ensure Redis is running
- Check Anthropic API key is valid

### Authentication Errors

**Problem**: 401 Unauthorized errors

**Solutions**:
- Verify JWT token in localStorage
- Check token expiration (30 minutes)
- Re-login to get fresh token

### MCP Tool Errors

**Problem**: Tool execution failures

**Solutions**:
- Verify portfolio has holdings
- Check portfolio_manager library is installed
- Ensure market data is accessible (Yahoo Finance API)

## Contributing

1. Follow existing code patterns
2. Add tests for new features
3. Update documentation
4. Use Black for Python formatting
5. Use Prettier for JavaScript formatting

## License

MIT License - See root LICENSE file

## Support

- 📚 [API Documentation](http://localhost:8000/docs)
- 🐛 [Issue Tracker](https://github.com/yourusername/portfolio-manager/issues)
- 💬 [Discussions](https://github.com/yourusername/portfolio-manager/discussions)
