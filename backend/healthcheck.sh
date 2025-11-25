#!/bin/sh
# Health check script that uses Railway's PORT environment variable
PORT=${PORT:-8000}
curl -f http://localhost:${PORT}/ || exit 1
