#!/bin/bash
# Startup script for Episcopio - Unified deployment
# This script initializes and starts the unified application (API + Dashboard) in a single process
# 
# Deployment Architecture:
# - Single process running both API and Dashboard
# - Dashboard served at root path "/"
# - API endpoints available at "/api/v1/*"
# - Listens on port 8000 only (no separate port 8050)
# - Ideal for Azure Web App deployment
# 
# For reverse proxy setup (nginx/Application Gateway), configure:
# - EP_API_URL=/api/v1 (relative paths for same-process communication)
# - EP_SECURITY_CORS_ALLOWED_ORIGINS with your domain

set -e  # Exit on error

echo "=========================================="
echo "Starting Episcopio unified application..."
echo "=========================================="

# Print environment info
echo "Python version: $(python3 --version)"
echo "Working directory: $(pwd)"

# Activate Azure's pre-built virtual environment
# Azure Oryx extracts a pre-built virtual environment called 'antenv'
echo "Activating virtual environment..."

# Try to use Azure's antenv if it exists
if [ -d "antenv" ]; then
    echo "Found antenv (Azure Oryx virtual environment)"
    source antenv/bin/activate
elif [ -f "/opt/python/etc/profile.d/activate.sh" ]; then
    echo "Using Azure App Service Python environment"
    source /opt/python/etc/profile.d/activate.sh
elif [ -d "venv" ]; then
    echo "Using existing venv"
    source venv/bin/activate
else
    echo "WARNING: No virtual environment found, using system Python"
fi

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip --quiet
# Install root requirements first
pip install -r requirements.txt --quiet
# Install API-specific requirements
pip install -r api/requirements.txt --quiet
# Install Dashboard-specific requirements
pip install -r dashboard/requirements.txt --quiet

# Set default environment variables if not set
export EP_POSTGRES_HOST=${EP_POSTGRES_HOST:-localhost}
export EP_POSTGRES_USER=${EP_POSTGRES_USER:-episcopio}
export EP_POSTGRES_PASSWORD=${EP_POSTGRES_PASSWORD:-changeme}
export EP_POSTGRES_DATABASE=${EP_POSTGRES_DATABASE:-episcopio}
export EP_POSTGRES_PORT=${EP_POSTGRES_PORT:-5432}
export EP_REDIS_URL=${EP_REDIS_URL:-redis://localhost:6379/0}
# EP_API_URL: Use relative path for unified deployment
export EP_API_URL=${EP_API_URL:-/api/v1}

echo "Environment variables configured:"
echo "  EP_POSTGRES_HOST: ${EP_POSTGRES_HOST}"
echo "  EP_POSTGRES_DATABASE: ${EP_POSTGRES_DATABASE}"
echo "  EP_API_URL: ${EP_API_URL}"
echo "  EP_SECURITY_CORS_ALLOWED_ORIGINS: ${EP_SECURITY_CORS_ALLOWED_ORIGINS:-not set}"

# Start unified application (API + Dashboard in single process)
echo "=========================================="
echo "Starting unified application on port 8000..."
echo "  - Dashboard at: /"
echo "  - API at: /api/v1/*"
echo "=========================================="

# Use Gunicorn with Uvicorn workers for the unified FastAPI+Dash app
gunicorn api.unified:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile /tmp/app-access.log \
  --error-logfile /tmp/app-error.log \
  --log-level info \
  --timeout 120

# Capture exit code for logging
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "ERROR: Gunicorn exited with code $EXIT_CODE"
    echo "=== Error Log ==="
    tail -50 /tmp/app-error.log 2>/dev/null || echo "No error log found"
    exit $EXIT_CODE
fi

