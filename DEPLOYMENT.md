# Deployment Guide - Portfolio Manager with AI Chat

## Quick Start (Docker/Podman)

### Prerequisites
- Docker or Podman installed
- Anthropic API key (get from https://console.anthropic.com/)

### Steps

1. **Clone and navigate to repository**
   ```bash
   cd portfolio-manager
   ```

2. **Create .env file**
   ```bash
   cp backend/.env.example backend/.env
   ```

3. **Edit backend/.env and set your Anthropic API key**
   ```
   ANTHROPIC_API_KEY=your-anthropic-api-key-here
   SECRET_KEY=$(openssl rand -hex 32)
   ```

4. **Start all services**
   ```bash
   podman-compose up -d
   # or
   docker-compose up -d
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Manual Setup (Development)

### Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
python -c "from app.models.database import init_db; init_db()"

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

### Redis (Required)

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally
# macOS: brew install redis && redis-server
# Ubuntu: sudo apt-get install redis-server
```

## First-Time Usage

1. **Register a new account**
   - Navigate to http://localhost:3000/register
   - Create account with email, username, password

2. **Login**
   - Go to http://localhost:3000/login
   - Enter credentials

3. **Create a portfolio**
   - Navigate to "Portfolios"
   - Click "Create Portfolio"
   - Add holdings (tickers and weights must sum to 1.0)
   - Example:
     ```
     AAPL: 0.30
     GOOGL: 0.25
     MSFT: 0.25
     TSLA: 0.20
     ```

4. **Start chatting**
   - Navigate to "AI Chat"
   - Ask questions like:
     - "What are my portfolio's risk metrics?"
     - "Simulate increasing AAPL by 10%"
     - "Run a Monte Carlo simulation"

## Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v --cov=app
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Environment Variables

### Backend (.env)

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-xxx
SECRET_KEY=your-secret-key-32-bytes

# Optional (defaults shown)
REDIS_HOST=localhost
REDIS_PORT=6379
DATABASE_URL=sqlite:///./portfolio.db
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend

```bash
# Optional
REACT_APP_API_URL=http://localhost:8000
```

## Troubleshooting

### "Connection refused" errors
- Ensure Redis is running: `redis-cli ping` should return "PONG"
- Check backend is running: `curl http://localhost:8000/health`

### "401 Unauthorized"
- Token expired (30 min) - re-login
- Check token in browser localStorage

### Chat not streaming
- Verify ANTHROPIC_API_KEY is set correctly
- Check browser console for SSE errors
- Ensure CORS is configured for your frontend URL

### Import errors in backend
- Make sure you're in backend/ directory
- The portfolio_manager library must be installed: `pip install -e ../`

## Production Deployment

### Security Checklist
- [ ] Generate strong SECRET_KEY
- [ ] Set ANTHROPIC_API_KEY securely
- [ ] Configure CORS_ORIGINS to production domains only
- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable HTTPS
- [ ] Add rate limiting
- [ ] Setup monitoring and logging

### Recommended Stack
- **Database**: PostgreSQL or MySQL
- **Cache**: Redis Cluster
- **Backend**: Gunicorn + Uvicorn workers
- **Frontend**: Nginx serving built React app
- **HTTPS**: Let's Encrypt + Nginx reverse proxy

## Support

- 📚 Documentation: See `docs/CHAT_FEATURE.md`
- 🐛 Issues: GitHub Issues
- 💬 Questions: GitHub Discussions
