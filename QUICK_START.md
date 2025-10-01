# Quick Start Guide

## Quick Start (Automated)

**Windows:**
```bash
.\start.bat
```

**Linux/macOS:**
```bash
chmod +x start.sh
./start.sh
```

This will automatically start Redis. Then follow the on-screen instructions to start the backend and frontend.

---

## Manual Setup

### 1. Start Redis with Podman

```bash
# Pull and run Redis container
podman run -d --name redis -p 6379:6379 redis:latest

# Verify Redis is running
podman ps | grep redis
```

**Stop Redis when done:**
```bash
podman stop redis
```

**Start existing Redis container:**
```bash
podman start redis
```

### 2. Backend Setup with UV

```bash
# Sync dependencies with uv (from project root)
uv sync

# Run backend with uvicorn
uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 4. Environment Variables

Create/update `.env` files:

**backend/.env:**
```env
REDIS_URL=redis://localhost:6379/0
FINNHUB_API_KEY=your_api_key_here
DATABASE_URL=sqlite+aiosqlite:///./portfolio.db
SECRET_KEY=your_secret_key_here
```

**frontend/.env:**
```env
VITE_API_URL=http://127.0.0.1:8000/api/v1
```

## What's New

### 🚀 Live Stock Chart
- Historical data shown immediately on login
- Real-time WebSocket updates every 15 seconds
- Up to 200 historical data points cached
- Auto-reconnect on disconnect

### ⚡ Fast Dashboard Loading
- Redis caching for all heavy operations
- Instant page loads after first visit
- No more "failed to load data" errors

### ✨ Instant Login Redirect
- Login → Dashboard in <1 second
- No more 10-second wait
- Smooth user experience

## Verify Installation

1. **Check Redis:** `podman exec redis redis-cli ping` → should return `PONG`
2. **Check Backend:** Visit `http://localhost:8000/docs`
3. **Check Frontend:** Visit `http://localhost:5173`
4. **Check WebSocket:** Look for green "Live (WebSocket)" indicator on Live Market page

## Troubleshooting

**Redis not running?**
```bash
podman start redis
# Or create new container if it doesn't exist
podman run -d --name redis -p 6379:6379 redis:latest
```

**WebSocket not connecting?**
- Check backend logs for errors
- Verify Redis is running: `podman ps | grep redis`
- Check firewall settings

**No historical data on chart?**
- Wait 30 seconds for background task to collect data
- Check Redis: `podman exec redis redis-cli KEYS "stock:history:*"`
- Refresh the page

**Check Redis data:**
```bash
# List all cached stock history keys
podman exec redis redis-cli KEYS "stock:history:*"

# View cached data for a specific symbol
podman exec redis redis-cli LRANGE "stock:history:AAPL" 0 -1

# Check active symbols
podman exec redis redis-cli GET "active:symbols"

# View all keys
podman exec redis redis-cli KEYS "*"
```

**UV sync issues?**
```bash
# Clear cache and re-sync
uv cache clean
uv sync --refresh
```

## Support

For detailed information, see [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
