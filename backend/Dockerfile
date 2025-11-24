FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies and build tools
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install setuptools and wheel first
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements from backend directory and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ .

# Expose port (Railway will set PORT env var)
EXPOSE 8000

# Health check (use $PORT if set, otherwise default to 8000)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/ || exit 1

# Run the application (production mode without --reload)
# Use Railway's $PORT environment variable if set, otherwise default to 8000
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
