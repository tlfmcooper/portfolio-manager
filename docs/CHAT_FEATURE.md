# AI-Powered Portfolio Chat Assistant - Documentation

## Overview

The AI-Powered Portfolio Chat Assistant is a comprehensive feature that enables natural language interaction with portfolio analytics, real-time rebalancing simulations, and financial guidance using the Model Context Protocol (MCP) and Claude AI.

## Architecture

### Backend (FastAPI)

```
backend/
├── app/
│   ├── main.py                    # FastAPI application entry point
│   ├── core/
│   │   ├── config.py              # Application settings
│   │   └── redis_client.py        # Redis async client
│   ├── services/
│   │   ├── mcp_server.py          # MCP portfolio analytics tools
│   │   └── chat_service.py        # Chat orchestration & AI integration
│   ├── api/v1/
│   │   ├── chat.py                # Chat endpoints (SSE streaming)
│   │   └── analysis.py            # Portfolio analysis endpoints
│   ├── schemas/
│   │   └── chat.py                # Pydantic models
│   └── tests/
│       ├── test_mcp_tools.py
│       ├── test_chat_api.py
│       └── test_chat_service.py
```

### Frontend (React + Vite)

```
frontend/
├── src/
│   ├── pages/
│   │   ├── Chat.jsx               # Main chat interface
│   │   ├── Dashboard.jsx          # Portfolio dashboard
│   │   └── Login.jsx              # Authentication
│   ├── components/
│   │   ├── Layout.jsx             # App layout with navigation
│   │   ├── ChatMessage.jsx        # Individual message component
│   │   ├── ChatInput.jsx          # Message input with streaming
│   │   └── DashboardPreview.jsx   # Inline dashboard visualizations
│   ├── hooks/
│   │   └── useChat.js             # Custom chat logic hook
│   └── contexts/
│       └── AuthContext.jsx        # Authentication context
```

## Features

### 1. MCP Portfolio Analytics Tools

The system provides 10 comprehensive portfolio analysis tools:

#### Portfolio Analysis
- **get_portfolio_summary**: Get portfolio overview (value, holdings, last update)
- **calculate_portfolio_metrics**: Performance metrics (returns, Sharpe, volatility, max drawdown)
- **get_sector_allocation**: Sector breakdown by percentage
- **get_risk_metrics**: Risk analysis (VaR, CVaR, beta, correlations)

#### Simulations & Optimization
- **simulate_rebalancing**: Model allocation changes and compare metrics
- **run_efficient_frontier**: Calculate optimal risk-return portfolios
- **run_monte_carlo**: Project portfolio scenarios (1000+ simulations)
- **run_cppi_simulation**: Dynamic risk management strategy

#### Dashboard Management
- **regenerate_full_dashboard**: Refresh all analytics with new parameters
- **get_performance_comparison**: Before/after rebalancing analysis

### 2. Chat Interface

#### User Experience
- Clean, Material-UI based chat interface
- Real-time streaming responses via Server-Sent Events (SSE)
- Portfolio selector for multi-portfolio support
- Message history with timestamps
- Inline dashboard visualizations

#### AI Assistant Capabilities
- Natural language understanding of portfolio questions
- Automatic tool selection and execution
- Educational explanations of financial concepts
- Risk warnings for high-volatility changes
- Actionable recommendations

### 3. Redis Caching

#### Session Management
```python
# Cache structure
Key: f"chat:session:{user_id}:{session_id}"
TTL: 30 days (2,592,000 seconds)

Value: {
    "session_id": str,
    "user_id": int,
    "messages": [...],
    "dashboard_snapshots": [...],
    "created_at": datetime,
    "last_activity": datetime
}
```

#### Performance Optimization
- Dashboard calculations cached (5 minutes)
- Market data cached (1 minute during trading, 1 hour after hours)
- Chat sessions persisted for 30 days

## API Endpoints

### Chat Endpoints

#### POST /api/v1/chat/sessions
Create new chat session
```json
Request:
{
  "user_id": 1
}

Response:
{
  "session_id": "uuid",
  "created_at": "2024-01-01T00:00:00"
}
```

#### GET /api/v1/chat/sessions/{session_id}
Retrieve chat history
```json
Response:
{
  "session_id": "uuid",
  "user_id": 1,
  "messages": [...],
  "dashboard_snapshots": [...],
  "created_at": "...",
  "last_activity": "..."
}
```

#### POST /api/v1/chat/sessions/{session_id}/messages
Send message and stream AI response (SSE)
```json
Request:
{
  "content": "What if I decrease AAPL by 10%?",
  "portfolio_id": 1
}

SSE Response Events:
event: message_delta
data: {"content": "Analyzing..."}

event: tool_call
data: {"name": "simulate_rebalancing", "parameters": {...}}

event: dashboard_update
data: {"type": "efficient_frontier", "data": {...}}

event: message_complete
data: {"content": "Full response text"}
```

#### DELETE /api/v1/chat/sessions/{session_id}
Delete chat session

### Analysis Endpoints

- `GET /api/v1/analysis/portfolios/{id}/summary`
- `GET /api/v1/analysis/portfolios/{id}/metrics`
- `GET /api/v1/analysis/portfolios/{id}/sector-allocation`
- `GET /api/v1/analysis/portfolios/{id}/risk-metrics`
- `GET /api/v1/analysis/portfolios/{id}/efficient-frontier`
- `GET /api/v1/analysis/portfolios/{id}/monte-carlo?scenarios=1000&time_horizon=252`
- `GET /api/v1/analysis/portfolios/{id}/cppi?multiplier=3.0&floor=0.8`
- `POST /api/v1/analysis/portfolios/{id}/simulate-rebalancing`

## Example Interactions

### Scenario 1: Portfolio Rebalancing

**User:** "What would happen if I decreased AAPL by 10% and increased QBTS by 50%?"

**AI Actions:**
1. Parse allocation changes: `{"AAPL": -10, "QBTS": 50}`
2. Call `simulate_rebalancing` tool
3. Calculate new metrics
4. Generate comparison dashboard

**AI Response:**
```
Based on your proposed rebalancing:
- Risk: Volatility increases from 18.5% → 22.3% (higher risk)
- Return: Expected annual return increases from 12.1% → 14.7%
- Sharpe Ratio: Improves from 0.65 → 0.67
- Diversification: Score decreases from 0.82 → 0.75

⚠️ Warning: QBTS is high-volatility. This significantly increases risk exposure.

Would you like to see a Monte Carlo simulation?
```

### Scenario 2: Risk Analysis

**User:** "I'm concerned about market volatility. How can I reduce risk?"

**AI Actions:**
1. Call `get_risk_metrics`
2. Analyze VaR, CVaR, volatility
3. Call `run_cppi_simulation`
4. Generate risk comparison

**AI Response:**
```
Your current portfolio has:
- 95% VaR: -$8,450 (max expected daily loss)
- 99% VaR: -$12,300 (extreme scenario)
- Volatility: 22.3% annualized

To reduce risk:
1. CPPI Strategy: Dynamically adjusts exposure
   - Reduces drawdown by 35%
   - Captures 78% of upside
2. Rebalancing: Decrease QBTS (25% → 15%), Increase bonds (10% → 20%)
   - Expected volatility: 22.3% → 17.8%

Would you like me to simulate these adjustments?
```

## Setup & Deployment

### Prerequisites
- Python 3.11+
- Node.js 18+
- Redis 7+
- Anthropic API key

### Backend Setup

```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings (ANTHROPIC_API_KEY, etc.)

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### Docker/Podman Deployment

```bash
# Start all services (Redis, Backend, Frontend)
podman-compose up -d

# View logs
podman-compose logs -f

# Stop services
podman-compose down
```

## Testing

### Backend Tests

```bash
cd backend
pytest app/tests/ -v

# With coverage
pytest app/tests/ --cov=app --cov-report=html
```

### Frontend Tests

```bash
cd frontend
npm test

# Coverage
npm test -- --coverage
```

## Configuration

### Environment Variables

```bash
# API Configuration
API_V1_STR=/api/v1
ALLOWED_ORIGINS=http://localhost:3000

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
CHAT_SESSION_TTL=2592000

# Anthropic
ANTHROPIC_API_KEY=your-key-here

# JWT
SECRET_KEY=your-secret-key
```

### Redis Cache TTLs

- Chat sessions: 30 days (2,592,000 seconds)
- Dashboard calculations: 5 minutes (300 seconds)
- Market data: 1 minute (60 seconds)

## Security Considerations

### Authentication
- All endpoints require JWT token validation
- User can only access their own chat sessions
- Portfolio ownership verified before analytics

### Rate Limiting
- Expensive simulations rate-limited per user
- SSE connections monitored for abuse
- Tool execution timeout protection

### Data Privacy
- Chat sessions isolated by user_id
- Sensitive portfolio data encrypted in transit
- Redis data expires automatically

## Performance Optimization

### Caching Strategy
1. **Session Cache**: 30-day persistence for chat history
2. **Analytics Cache**: 5-minute TTL for dashboard calculations
3. **Market Data Cache**: 1-minute refresh during trading hours

### Streaming Optimization
- SSE for efficient real-time updates
- Chunked transfer encoding
- Message delta streaming (not full responses)

### Frontend Optimization
- React.memo for message components
- Virtualization for long message lists
- Debounced user input
- Optimistic UI updates

## Troubleshooting

### Common Issues

**Issue: Chat not streaming**
- Check ANTHROPIC_API_KEY is set
- Verify Redis connection
- Check browser SSE support

**Issue: Dashboard not updating**
- Clear Redis cache
- Check portfolio_id parameter
- Verify MCP tool execution

**Issue: Authentication errors**
- Regenerate JWT token
- Check token expiration
- Verify CORS settings

## Future Enhancements

### Planned Features
- [ ] Multi-language support
- [ ] Voice input/output
- [ ] Custom portfolio strategies
- [ ] Integration with live trading APIs
- [ ] Advanced visualization options
- [ ] Export chat history
- [ ] Collaborative portfolio analysis

### Integration Opportunities
- Public finance MCPs (Yahoo Finance, Alpha Vantage)
- Real-time market data feeds
- Trading platform APIs (Alpaca, Interactive Brokers)
- News sentiment analysis
- Economic calendar integration

## Support

For issues, questions, or feature requests:
- GitHub Issues: https://github.com/tlfmcooper/portfolio-manager/issues
- Documentation: /docs
- API Docs: http://localhost:8000/docs

## License

MIT License - see LICENSE file for details
