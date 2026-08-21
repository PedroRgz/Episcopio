"""Unified application - FastAPI with the Dash dashboard.

A single ASGI app serving:

* the Dash dashboard at ``/`` (root)
* the API at ``/api/v1/*``

Running one process keeps deployment simple (one port, no inter-service HTTP)
and lets the dashboard read the core services in-process instead of calling
itself over the network.
"""
import logging
import os
import sys

logging.basicConfig(level=os.getenv("EP_LOG_LEVEL", "INFO").upper())
logger = logging.getLogger("unified")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# starlette.middleware.wsgi.WSGIMiddleware is deprecated and removed in recent
# Starlette releases; a2wsgi is the maintained replacement and is also faster.
try:
    from a2wsgi import WSGIMiddleware
except ImportError:  # pragma: no cover - fallback for older environments
    from starlette.middleware.wsgi import WSGIMiddleware  # type: ignore

from api.main import app as fastapi_app  # noqa: E402
from dashboard.app import build_dashboard_app  # noqa: E402

_dashboard_state = {"mounted": False}


@fastapi_app.get("/__unified_ping", include_in_schema=False)
def unified_ping():
    """Diagnostic endpoint to verify the unified deployment."""
    return {
        "unified": True,
        "dash_loaded": _dashboard_state["mounted"],
        "dashboard_mount": "/" if _dashboard_state["mounted"] else None,
        "api_prefix": "/api/v1",
    }


logger.info("Building Dash application for root mount point...")
try:
    dash_app = build_dashboard_app(requests_pathname_prefix="/")
    # Mounted last so the API routes declared above keep precedence over the
    # catch-all Dash mount at '/'.
    fastapi_app.mount("/", WSGIMiddleware(dash_app.server))
    _dashboard_state["mounted"] = True
    logger.info("Dash mounted at '/' - FastAPI + Dash unified")
except Exception:
    # The API stays up so /api/v1/health still reports, but a missing
    # dashboard is a deployment failure and must be loud in the logs.
    logger.exception("Failed to build or mount the dashboard")
    _dashboard_state["mounted"] = False

app = fastapi_app
