"""Unified application - FastAPI with Dash dashboard mounted at root.

This module creates a single application that serves:
- Dashboard (Dash/Plotly) at the root path "/"
- API endpoints (FastAPI) at "/api/v1/*"

This unified approach simplifies deployment to Azure App Service by:
- Running a single process on port 8000
- Eliminating the need for port 8050
- Enabling relative API URLs ("/api/v1") for inter-service communication
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from starlette.middleware.wsgi import WSGIMiddleware
from api.main import app as fastapi_app
from dashboard.app import build_dashboard_app

# Build the Dash application
dash_app = build_dashboard_app(requests_pathname_prefix="/dashboard/")

# Mount the Dash Flask server onto FastAPI at '/dashboard' path
# This makes the Dashboard accessible at "/dashboard" and keeps API at "/api/v1/*"
fastapi_app.mount("/dashboard", WSGIMiddleware(dash_app.server))

# Export the unified app as the main application
# Gunicorn will use this: api.unified:app
app = fastapi_app
