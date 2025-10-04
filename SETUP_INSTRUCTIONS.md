# Portfolio Manager - Setup Instructions

## Quick Start

This guide will help you set up and run the AI-Powered Portfolio Chat Assistant.

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Redis 7+** (or use Docker/Podman)
- **Anthropic API Key** (get one at https://console.anthropic.com/)

## Option 1: Docker/Podman (Recommended)

### Step 1: Configure Environment

```bash
# Clone the repository
git clone https://github.com/tlfmcooper/portfolio-manager.git
cd portfolio-manager

# Create backend .env file
cp backend/.env.example backend/.env

# Edit backend/.env and add your Anthropic API key
# ANTHROPIC_API_KEY=sk-ant-...
```

### Step 2: Start All Services

```bash
# Using Docker Compose
docker-compose up -d

# OR using Podman Compose
podman-compose up -d
```

### Step 3: Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Redis**: localhost:6379

## Option 2: Manual Setup

### Step 1: Install Redis

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis
```

**Windows:**
- Download from https://redis.io/download
- Or use WSL2

### Step 2: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000

### Step 3: Frontend Setup

```bash
# In a new terminal
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will be available at: http://localhost:3000

## Verification

### Test Backend

```bash
# Health check
curl http://localhost:8000/health

# Expected: {"status":"healthy"}
```

### Test Redis

```bash
redis-cli ping

# Expected: PONG
```

### Test Frontend

1. Open http://localhost:3000
2. Login with any credentials (demo mode)
3. Navigate to "AI Chat"
4. Try asking: "What are my current portfolio metrics?"

## Configuration

### Backend Environment Variables

Edit `backend/.env`:

```bash
# Anthropic API (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Redis (default values work for local setup)
REDIS_HOST=localhost
REDIS_PORT=6379

# CORS (add your frontend URLs)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Cache TTLs (seconds)
CHAT_SESSION_TTL=2592000  # 30 days
DASHBOARD_CACHE_TTL=300   # 5 minutes
MARKET_DATA_CACHE_TTL=60  # 1 minute

# JWT Secret (change in production!)
SECRET_KEY=your-secret-key-change-in-production
```

### Frontend Configuration

The frontend uses Vite proxy to connect to the backend. No additional configuration needed for local development.

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm test -- --coverage
```

## Development Workflow

### Starting Development

1. **Terminal 1 - Backend:**
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn app.main:app --reload
   ```

2. **Terminal 2 - Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Terminal 3 - Redis:**
   ```bash
   redis-server
   # Or: brew services start redis
   ```

### Accessing Services

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Interactive API: http://localhost:8000/redoc

## Troubleshooting

### Backend Issues

**Issue: ModuleNotFoundError**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Issue: Redis Connection Error**
```bash
# Check Redis is running
redis-cli ping

# Start Redis if needed
redis-server
```

**Issue: Anthropic API Error**
```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Or check .env file
cat backend/.env | grep ANTHROPIC
```

### Frontend Issues

**Issue: Port Already in Use**
```bash
# Change port in vite.config.js
# Or kill process using port 3000
lsof -ti:3000 | xargs kill
```

**Issue: API Connection Failed**
```bash
# Verify backend is running
curl http://localhost:8000/health

# Check proxy configuration in vite.config.js
```

### Docker/Podman Issues

**Issue: Container Won't Start**
```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs redis

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up
```

## Production Deployment

### Security Checklist

- [ ] Change `SECRET_KEY` in .env
- [ ] Set strong `REDIS_PASSWORD`
- [ ] Use HTTPS for all connections
- [ ] Enable CORS only for trusted origins
- [ ] Set up proper JWT token validation
- [ ] Enable rate limiting
- [ ] Configure firewall rules

### Environment Setup

```bash
# Set production environment variables
export ENVIRONMENT=production
export DEBUG=false

# Use production-grade WSGI server
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Build optimized frontend
cd frontend
npm run build
```

### Recommended Production Stack

- **Web Server**: Nginx or Caddy (reverse proxy)
- **Backend**: Gunicorn + Uvicorn workers
- **Frontend**: Static build served by Nginx
- **Redis**: Redis Sentinel for high availability
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack or Loki

## Additional Resources

- **Documentation**: See `docs/CHAT_FEATURE.md`
- **API Reference**: http://localhost:8000/docs
- **GitHub Issues**: https://github.com/tlfmcooper/portfolio-manager/issues

## Support

For help:
1. Check documentation in `/docs` folder
2. Review API docs at `/docs` endpoint
3. Open an issue on GitHub
4. Check logs for detailed error messages

## License

MIT License - see LICENSE file for details
