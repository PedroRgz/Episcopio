#!/bin/bash
# Startup script for Azure Web App / Production Deployment
# This script initializes and starts both the API and Dashboard services
# 
# For Azure Web App deployment, both services run on the same host behind a reverse proxy.
# The Dashboard runs on port 8050 (default) and API on port 8000.
# Azure can expose either service through a single port using WEBSITES_PORT environment variable.
# For production, use a reverse proxy (nginx, Azure App Gateway) to route:
#   - /api/* -> API service (port 8000)
#   - /* -> Dashboard service (port 8050)

set -e  # Exit on error

echo "=========================================="
echo "Starting Episcopio application..."
echo "=========================================="

# Print environment info
echo "Python version: $(python3 --version)"
echo "Working directory: $(pwd)"
echo "WEBSITES_PORT: ${WEBSITES_PORT:-not set}"

# Check if curl is available (needed for health checks)
if ! command -v curl &> /dev/null; then
    echo "WARNING: curl is not available. Health checks will be skipped."
    CURL_AVAILABLE=false
else
    CURL_AVAILABLE=true
fi

# Install dependencies if not already installed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# Set default environment variables if not set
export EP_POSTGRES_HOST=${EP_POSTGRES_HOST:-localhost}
export EP_POSTGRES_USER=${EP_POSTGRES_USER:-episcopio}
export EP_POSTGRES_PASSWORD=${EP_POSTGRES_PASSWORD:-changeme}
export EP_POSTGRES_DATABASE=${EP_POSTGRES_DATABASE:-episcopio}
export EP_POSTGRES_PORT=${EP_POSTGRES_PORT:-5432}
export EP_REDIS_URL=${EP_REDIS_URL:-redis://localhost:6379/0}
export EP_API_URL=${EP_API_URL:-http://localhost:8000}

echo "Environment variables configured:"
echo "  EP_POSTGRES_HOST: ${EP_POSTGRES_HOST}"
echo "  EP_POSTGRES_DATABASE: ${EP_POSTGRES_DATABASE}"
echo "  EP_API_URL: ${EP_API_URL}"
echo "  EP_SECURITY_CORS_ALLOWED_ORIGINS: ${EP_SECURITY_CORS_ALLOWED_ORIGINS:-not set}"

# Start API in background
echo "=========================================="
echo "Starting API service on port 8000..."
echo "=========================================="
cd api
python main.py > /tmp/api.log 2>&1 &
API_PID=$!
cd ..

echo "API started with PID: $API_PID"

# Wait for API to be ready using health check with retries
export EP_API_WAIT_SECONDS=${EP_API_WAIT_SECONDS:-30}
echo "Waiting for API to be ready (timeout: ${EP_API_WAIT_SECONDS}s)..."
API_HEALTH_URL="${EP_API_URL}/api/v1/health"
SECONDS_WAITED=0

if [ "$CURL_AVAILABLE" = true ]; then
    until curl --silent --fail "$API_HEALTH_URL" > /dev/null 2>&1; do
        sleep 2
        SECONDS_WAITED=$((SECONDS_WAITED+2))
        echo "  Waiting for API... (${SECONDS_WAITED}s/${EP_API_WAIT_SECONDS}s)"
        
        # Check if API process is still running
        if ! kill -0 $API_PID 2>/dev/null; then
            echo "ERROR: API process died. Check logs:"
            cat /tmp/api.log
            exit 1
        fi
        
        if [ "$SECONDS_WAITED" -ge "$EP_API_WAIT_SECONDS" ]; then
            echo "WARNING: API did not become ready after ${EP_API_WAIT_SECONDS} seconds."
            echo "API logs:"
            cat /tmp/api.log
            echo "Continuing anyway to start Dashboard..."
            break
        fi
    done

    if curl --silent --fail "$API_HEALTH_URL" > /dev/null 2>&1; then
        echo "✓ API is ready and responding!"
    else
        echo "⚠ API may not be fully ready, but continuing..."
    fi
else
    # If curl is not available, just wait for a fixed time
    echo "  Waiting ${EP_API_WAIT_SECONDS}s for API to start (curl not available for health check)..."
    sleep "$EP_API_WAIT_SECONDS"
    
    # Check if API process is still running
    if kill -0 $API_PID 2>/dev/null; then
        echo "✓ API process is running"
    else
        echo "ERROR: API process died. Check logs:"
        cat /tmp/api.log
        exit 1
    fi
fi

# Start Dashboard on the port Azure expects
echo "=========================================="
echo "Starting Dashboard service on port 8050..."
echo "=========================================="
cd dashboard
python app.py > /tmp/dashboard.log 2>&1 &
DASHBOARD_PID=$!
cd ..

echo "Dashboard started with PID: $DASHBOARD_PID"

# Wait a moment for dashboard to start
sleep 3

# Check if dashboard is running
if kill -0 $DASHBOARD_PID 2>/dev/null; then
    echo "✓ Dashboard is running"
else
    echo "ERROR: Dashboard failed to start. Check logs:"
    cat /tmp/dashboard.log
    exit 1
fi

echo "=========================================="
echo "Application started successfully!"
echo "=========================================="
echo "API PID: $API_PID"
echo "Dashboard PID: $DASHBOARD_PID"
echo "API available at: http://localhost:8000"
echo "Dashboard available at: http://localhost:8050"
echo "=========================================="
echo "Logs available at:"
echo "  API: /tmp/api.log"
echo "  Dashboard: /tmp/dashboard.log"
echo "=========================================="

# Function to handle shutdown
shutdown_handler() {
    echo ""
    echo "Shutting down services..."
    kill $API_PID 2>/dev/null || true
    kill $DASHBOARD_PID 2>/dev/null || true
    exit 0
}

# Trap signals for graceful shutdown
trap shutdown_handler SIGTERM SIGINT

# Keep script running and monitor processes
while true; do
    if ! kill -0 $API_PID 2>/dev/null; then
        echo "ERROR: API process died!"
        cat /tmp/api.log
        exit 1
    fi
    
    if ! kill -0 $DASHBOARD_PID 2>/dev/null; then
        echo "ERROR: Dashboard process died!"
        cat /tmp/dashboard.log
        exit 1
    fi
    
    sleep 10
done
