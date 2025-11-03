#!/bin/bash
# Startup script for Azure Web App
# This script initializes and starts both the API and Dashboard services

echo "Starting Episcopio application..."

# Install dependencies if not already installed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Set default environment variables if not set
export EP_POSTGRES_HOST=${EP_POSTGRES_HOST:-localhost}
export EP_POSTGRES_USER=${EP_POSTGRES_USER:-episcopio}
export EP_POSTGRES_PASSWORD=${EP_POSTGRES_PASSWORD:-changeme}
export EP_POSTGRES_DATABASE=${EP_POSTGRES_DATABASE:-episcopio}
export EP_POSTGRES_PORT=${EP_POSTGRES_PORT:-5432}
export EP_REDIS_URL=${EP_REDIS_URL:-redis://localhost:6379/0}
export EP_API_URL=${EP_API_URL:-http://localhost:8000}

# Start API in background
echo "Starting API service on port 8000..."
cd api
python main.py &
API_PID=$!
cd ..

# Wait for API to be ready using health check with retries
export EP_API_WAIT_SECONDS=${EP_API_WAIT_SECONDS:-5}
echo "Waiting for API to be ready (timeout: ${EP_API_WAIT_SECONDS}s)..."
API_HEALTH_URL="${EP_API_URL}/health"
SECONDS_WAITED=0
until curl --silent --fail "$API_HEALTH_URL" > /dev/null; do
    sleep 1
    SECONDS_WAITED=$((SECONDS_WAITED+1))
    if [ "$SECONDS_WAITED" -ge "$EP_API_WAIT_SECONDS" ]; then
        echo "API did not become ready after ${EP_API_WAIT_SECONDS} seconds. Exiting."
        exit 1
    fi
done
echo "API is ready!"

# Start Dashboard
echo "Starting Dashboard service on port 8050..."
cd dashboard
python app.py &
DASHBOARD_PID=$!
cd ..

echo "Application started successfully!"
echo "API PID: $API_PID"
echo "Dashboard PID: $DASHBOARD_PID"
echo "API available at: http://localhost:8000"
echo "Dashboard available at: http://localhost:8050"

# Keep script running
wait
