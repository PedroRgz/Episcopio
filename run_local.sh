#!/bin/bash
# Local development script - runs without Docker
# This script is simpler than startup.sh for local development

set -e

echo "🚀 Starting Episcopio locally..."

# Set default environment variables for local development
export EP_POSTGRES_HOST=${EP_POSTGRES_HOST:-localhost}
export EP_POSTGRES_USER=${EP_POSTGRES_USER:-episcopio}
export EP_POSTGRES_PASSWORD=${EP_POSTGRES_PASSWORD:-changeme}
export EP_POSTGRES_DATABASE=${EP_POSTGRES_DATABASE:-episcopio}
export EP_POSTGRES_PORT=${EP_POSTGRES_PORT:-5432}
export EP_REDIS_URL=${EP_REDIS_URL:-redis://localhost:6379/0}
export EP_API_URL=${EP_API_URL:-http://localhost:8000}

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "✅ Setup complete!"
echo ""
echo "Starting services..."
echo "  API: http://localhost:8000"
echo "  Dashboard: http://localhost:8050"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $API_PID $DASHBOARD_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start API in background
cd api
python main.py &
API_PID=$!
cd ..

# Wait for API to start
sleep 3

# Start Dashboard in background
cd dashboard
python app.py &
DASHBOARD_PID=$!
cd ..

echo "✨ Services started!"
echo ""

# Wait for processes
wait
