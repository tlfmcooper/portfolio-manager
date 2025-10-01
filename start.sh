#!/bin/bash

# Portfolio Dashboard Startup Script

echo "🚀 Starting Portfolio Dashboard..."
echo ""

# Check if Podman is installed
if ! command -v podman &> /dev/null; then
    echo "❌ Podman is not installed. Please install Podman first."
    exit 1
fi

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed. Please install UV first."
    echo "   Run: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Start Redis container
echo "📦 Starting Redis container..."
if podman ps -a | grep -q redis; then
    if podman ps | grep -q redis; then
        echo "✅ Redis is already running"
    else
        echo "🔄 Starting existing Redis container..."
        podman start redis
    fi
else
    echo "🔄 Creating new Redis container..."
    podman run -d --name redis -p 6379:6379 redis:latest
fi

# Verify Redis is running
sleep 2
if podman exec redis redis-cli ping &> /dev/null; then
    echo "✅ Redis is running"
else
    echo "❌ Redis failed to start"
    exit 1
fi

echo ""
echo "📝 To start the backend, run:"
echo "   uv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "📝 To start the frontend, run in a new terminal:"
echo "   cd frontend && npm run dev"
echo ""
echo "🎉 Redis is ready! Start the backend and frontend to complete the setup."
