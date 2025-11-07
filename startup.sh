#!/bin/bash
# Startup script for Episcopio - supports multiple deployment scenarios
# This script initializes and starts both the API and Dashboard services on the same host
# 
# Deployment Scenarios:
# 1. Azure Web App: Both services run on same host, exposed through WEBSITES_PORT
#    - Set EP_API_URL=http://localhost:8000 (services communicate via localhost)
#    - Azure routes external traffic to Dashboard port
# 
# 2. Azure VM with reverse proxy (nginx):
#    - Set EP_API_URL=/api (Dashboard uses relative paths)
#    - Nginx routes /api/* to port 8000, /* to port 8050
#    - Only nginx ports (80/443) are exposed publicly
# 
# 3. Local development:
#    - Set EP_API_URL=http://localhost:8000 (services on different ports)
#    - Both ports (8000, 8050) accessible directly
# 
# For reverse proxy setup, remember to configure EP_SECURITY_CORS_ALLOWED_ORIGINS with your domain

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

# Activate Azure's pre-built virtual environment
# Azure Oryx extracts a pre-built virtual environment called 'antenv'
# We need to use it instead of creating a new one
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
# EP_API_URL configuration depends on deployment scenario:
# - Same host, separate ports (Azure Web App, local dev): http://localhost:8000
# - Behind reverse proxy (Azure VM with nginx): /api
# This script starts both services on the same host, so default to localhost:8000
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
# Use Gunicorn with Uvicorn workers for production
gunicorn main:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile /tmp/api-access.log \
  --error-logfile /tmp/api-error.log \
  --log-level info \
  --daemon
cd ..

# Get the PID of the gunicorn master process
sleep 2
API_PID=$(pgrep -f "gunicorn main:app" | head -1)
if [ -z "$API_PID" ]; then
    echo "ERROR: Failed to get API process PID"
    echo "=== API Error Log ==="
    cat /tmp/api-error.log 2>/dev/null || echo "No error log found"
    exit 1
fi
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
            echo "=== API Error Log ==="
            cat /tmp/api-error.log 2>/dev/null || echo "No error log found"
            echo "=== API Access Log ==="
            tail -20 /tmp/api-access.log 2>/dev/null || echo "No access log found"
            exit 1
        fi
        
        if [ "$SECONDS_WAITED" -ge "$EP_API_WAIT_SECONDS" ]; then
            echo "WARNING: API did not become ready after ${EP_API_WAIT_SECONDS} seconds."
            echo "API logs:"
            echo "=== API Error Log ==="
            tail -50 /tmp/api-error.log 2>/dev/null || echo "No error log found"
            echo "=== API Access Log ==="
            tail -50 /tmp/api-access.log 2>/dev/null || echo "No access log found"
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
        echo "=== API Error Log ==="
        cat /tmp/api-error.log 2>/dev/null || echo "No error log found"
        echo "=== API Access Log ==="
        tail -20 /tmp/api-access.log 2>/dev/null || echo "No access log found"
        exit 1
    fi
fi

# Start Dashboard on the port Azure expects
echo "=========================================="
echo "Starting Dashboard service on port 8050..."
echo "=========================================="
cd dashboard
# Use Gunicorn for Dashboard (Dash app)
# The app instance is in app.py as 'app.server' (Flask server behind Dash)
gunicorn app:app.server \
  --workers 2 \
  --bind 0.0.0.0:8050 \
  --access-logfile /tmp/dashboard-access.log \
  --error-logfile /tmp/dashboard-error.log \
  --log-level info \
  --timeout 120 \
  --daemon
cd ..

# Get the PID of the gunicorn master process
sleep 2
DASHBOARD_PID=$(pgrep -f "gunicorn app:app.server" | head -1)
if [ -z "$DASHBOARD_PID" ]; then
    echo "ERROR: Failed to get Dashboard process PID"
    echo "=== Dashboard Error Log ==="
    cat /tmp/dashboard-error.log 2>/dev/null || echo "No error log found"
    exit 1
fi
echo "Dashboard started with PID: $DASHBOARD_PID"

# Wait a moment for dashboard to start
sleep 3

# Check if dashboard is running
if kill -0 $DASHBOARD_PID 2>/dev/null; then
    echo "✓ Dashboard is running"
else
    echo "ERROR: Dashboard failed to start. Check logs:"
    echo "=== Dashboard Error Log ==="
    cat /tmp/dashboard-error.log 2>/dev/null || echo "No error log found"
    echo "=== Dashboard Access Log ==="
    tail -20 /tmp/dashboard-access.log 2>/dev/null || echo "No access log found"
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
echo "  API Access: /tmp/api-access.log"
echo "  API Error: /tmp/api-error.log"
echo "  Dashboard Access: /tmp/dashboard-access.log"
echo "  Dashboard Error: /tmp/dashboard-error.log"
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
        echo "=== API Error Log ==="
        tail -50 /tmp/api-error.log 2>/dev/null || echo "No error log found"
        exit 1
    fi
    
    if ! kill -0 $DASHBOARD_PID 2>/dev/null; then
        echo "ERROR: Dashboard process died!"
        echo "=== Dashboard Error Log ==="
        tail -50 /tmp/dashboard-error.log 2>/dev/null || echo "No error log found"
        exit 1
    fi
    
    sleep 10
done
