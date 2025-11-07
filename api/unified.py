"""Unified application - FastAPI with Dash dashboard.

This module creates a single application that serves:
- Dashboard (Dash/Plotly) at "/" (root)
- API endpoints (FastAPI) at "/api/v1/*"

This unified approach simplifies deployment to Azure App Service by:
- Running a single process on port 8000
- Eliminating the need for port 8050
- Enabling relative API URLs ("/api/v1") for inter-service communication
"""
import sys
import os
import logging

# Add parent directory to path for imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from starlette.middleware.wsgi import WSGIMiddleware
from api.main import app as fastapi_app
from dashboard.app import build_dashboard_app

# Configure logging
logger = logging.getLogger("unified")
logging.basicConfig(level=logging.INFO)

# Add diagnostic endpoint before mounting Dashboard
@fastapi_app.get("/__unified_ping", include_in_schema=False)
def unified_ping():
    """Diagnostic endpoint to verify unified deployment."""
    return {
        "unified": True,
        "dash_loaded": True,
        "dashboard_mount": "/",
        "api_prefix": "/api/v1"
    }

# Build the Dash application with root path
logger.info("Building Dash application for root mount point...")
dash_app = build_dashboard_app(requests_pathname_prefix="/")

# Mount the Dash Flask server onto FastAPI at root '/' path
# This makes the Dashboard accessible at "/" and keeps API at "/api/v1/*"
logger.info("Mounting Dash at '/' (root) - FastAPI + Dash unified")
fastapi_app.mount("/", WSGIMiddleware(dash_app.server))
logger.info("Mount completed successfully")

# Export the unified app as the main application
# Gunicorn will use this: api.unified:app
app = fastapi_app
