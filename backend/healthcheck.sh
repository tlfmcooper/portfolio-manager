#!/bin/sh
# Health check script for containerized deployments
PORT=${PORT:-8000}
curl -f http://localhost:${PORT}/ || exit 1
