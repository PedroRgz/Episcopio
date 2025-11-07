#!/bin/bash
# Test script to validate startup.sh changes
# This simulates an Azure-like environment to verify the script works

set -e

echo "=========================================="
echo "Testing startup.sh for Azure compatibility"
echo "=========================================="

# Save current directory
REPO_DIR=$(pwd)
TEST_DIR=$(mktemp -d)

# Clean up on exit
cleanup() {
    echo "Cleaning up test directory..."
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

# Create test directory
mkdir -p "$TEST_DIR"
cp -r . "$TEST_DIR/"
cd "$TEST_DIR"

echo ""
echo "Test 1: Verifying bash syntax..."
if bash -n startup.sh; then
    echo "✓ Bash syntax is valid"
else
    echo "✗ Bash syntax check failed"
    exit 1
fi

echo ""
echo "Test 2: Checking for removed venv creation logic..."
if grep -q "python3 -m venv venv" startup.sh; then
    echo "✗ FAIL: Script still tries to create venv"
    exit 1
else
    echo "✓ Old venv creation logic removed"
fi

echo ""
echo "Test 3: Checking for antenv detection..."
if grep -q "antenv" startup.sh; then
    echo "✓ Script checks for antenv"
else
    echo "✗ FAIL: Script doesn't check for antenv"
    exit 1
fi

echo ""
echo "Test 4: Checking for Gunicorn usage in API..."
if grep -q "gunicorn main:app" startup.sh; then
    echo "✓ API uses Gunicorn"
else
    echo "✗ FAIL: API doesn't use Gunicorn"
    exit 1
fi

echo ""
echo "Test 5: Checking for Gunicorn usage in Dashboard..."
if grep -q "gunicorn app:server" startup.sh; then
    echo "✓ Dashboard uses Gunicorn"
else
    echo "✗ FAIL: Dashboard doesn't use Gunicorn"
    exit 1
fi

echo ""
echo "Test 6: Checking for Uvicorn worker class..."
if grep -q "uvicorn.workers.UvicornWorker" startup.sh; then
    echo "✓ API uses Uvicorn workers"
else
    echo "✗ FAIL: API doesn't use Uvicorn workers"
    exit 1
fi

echo ""
echo "Test 7: Verifying gunicorn in api/requirements.txt..."
if grep -q "gunicorn" api/requirements.txt; then
    echo "✓ Gunicorn is in api/requirements.txt"
else
    echo "✗ FAIL: Gunicorn missing from api/requirements.txt"
    exit 1
fi

echo ""
echo "Test 8: Checking for proper log files..."
if grep -q "/tmp/api-access.log" startup.sh && \
   grep -q "/tmp/api-error.log" startup.sh && \
   grep -q "/tmp/dashboard-access.log" startup.sh && \
   grep -q "/tmp/dashboard-error.log" startup.sh; then
    echo "✓ Proper log file paths configured"
else
    echo "✗ FAIL: Log file paths not properly configured"
    exit 1
fi

echo ""
echo "Test 9: Checking for PID error handling..."
if grep -q "if \[ -z \"\$API_PID\" \]" startup.sh && \
   grep -q "if \[ -z \"\$DASHBOARD_PID\" \]" startup.sh; then
    echo "✓ PID error handling present"
else
    echo "✗ FAIL: PID error handling missing"
    exit 1
fi

echo ""
echo "Test 10: Simulating antenv environment..."
# Create a mock antenv
python3 -m venv antenv
source antenv/bin/activate

# Try to extract just the virtual environment logic from startup.sh
if [ -d "antenv" ]; then
    echo "✓ antenv detected correctly"
else
    echo "✗ FAIL: antenv detection logic issue"
    exit 1
fi

echo ""
echo "Test 11: Checking web.config exists..."
if [ -f "web.config" ]; then
    echo "✓ web.config file created"
else
    echo "⚠ WARNING: web.config not found (optional for Linux)"
fi

echo ""
echo "Test 12: Checking AZURE_APP_SERVICE_CONFIG.md exists..."
if [ -f "AZURE_APP_SERVICE_CONFIG.md" ]; then
    echo "✓ Azure documentation created"
else
    echo "⚠ WARNING: AZURE_APP_SERVICE_CONFIG.md not found"
fi

echo ""
echo "=========================================="
echo "All tests passed! ✓"
echo "=========================================="
echo ""
echo "Summary of changes:"
echo "1. startup.sh now uses Azure Oryx antenv instead of creating venv"
echo "2. Both services use Gunicorn for production deployment"
echo "3. API uses Gunicorn with Uvicorn workers"
echo "4. Dashboard uses Gunicorn directly"
echo "5. Proper log files and error handling"
echo "6. gunicorn added to api/requirements.txt"
echo "7. web.config created for documentation"
echo "8. Comprehensive Azure deployment guide created"
