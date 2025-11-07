"""API client for Episcopio dashboard."""
import requests
from requests.exceptions import RequestException, ConnectionError, Timeout
import os
from typing import Optional, Dict, Any
from .sample_data_loader import sample_data_loader


# EP_API_URL configuration:
# - Azure VM with reverse proxy (nginx): /api (fallback code default, designed for reverse proxy scenarios)
# - Azure Web Apps (startup.sh) or Local dev (run_local.sh): http://localhost:8000 (set by startup scripts, overrides default)
# - Separate API domain: https://api.example.com (set via environment variable)
# 
# Note: In practice, startup.sh and run_local.sh always set EP_API_URL=http://localhost:8000,
# so the /api default is only used when running the dashboard standalone with a reverse proxy.
BASE_URL = os.getenv("EP_API_URL", "/api")
TIMEOUT = 30


class EpiscopioAPIClient:
    """Client for Episcopio API."""
    
    def __init__(self, base_url: str = BASE_URL, use_sample_data: bool = True):
        """Initialize the API client.
        
        Args:
            base_url: Base URL for the API endpoint
            use_sample_data: If True (default), uses sample data instead of real API calls.
                           This allows users to explore the application without configuring API keys.
        
        Note:
            The client defaults to sample data mode for demonstration purposes.
            Call set_api_keys() to switch to real API mode with actual platform credentials.
        """
        self.base_url = base_url.rstrip("/")
        self.use_sample_data = use_sample_data
        self.api_keys = {}
    
    def set_api_keys(self, keys: Dict[str, str]):
        """Set API keys for different platforms.
        
        Args:
            keys: Dictionary mapping platform names to API keys
                 (e.g., {'inegi': 'token', 'twitter': 'bearer_token'})
        
        Security Warning:
            API keys are stored in plain text in memory without encryption.
            For production use:
            - Implement proper secret management (e.g., HashiCorp Vault, AWS Secrets Manager)
            - Use environment variables or encrypted storage
            - Never commit API keys to version control
            - Consider using OAuth flows instead of storing credentials
            - Implement session timeout and key rotation policies
        """
        self.api_keys = keys
        # If any keys are provided, try to use real API
        if any(keys.values()):
            self.use_sample_data = False
    
    def set_sample_mode(self, use_sample: bool):
        """Set whether to use sample data."""
        self.use_sample_data = use_sample
    
    def health(self) -> Dict[str, Any]:
        """Check API health."""
        if self.use_sample_data:
            return {"status": "ok", "mode": "sample_data"}
        try:
            r = requests.get(f"{self.base_url}/api/v1/health", timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except RequestException:
            return {"status": "error", "mode": "api_unavailable"}
    
    def get_meta(self) -> Dict[str, Any]:
        """Get metadata about data sources."""
        if self.use_sample_data:
            return {
                "fuentes": ["sample_data"],
                "ultima_actualizacion": "2025-01-15T12:00:00Z"
            }
        r = requests.get(f"{self.base_url}/api/v1/meta", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    
    def get_kpis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get KPIs."""
        if self.use_sample_data:
            entidad = payload.get("entidad", "31")
            return sample_data_loader.get_kpis(entidad)
        r = requests.post(
            f"{self.base_url}/api/v1/kpi",
            json=payload,
            timeout=TIMEOUT
        )
        r.raise_for_status()
        return r.json()
    
    def get_timeseries(
        self,
        entidad: Optional[str] = None,
        morbilidad_id: Optional[int] = None,
        fecha_ini: Optional[str] = None,
        fecha_fin: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get time series data."""
        if self.use_sample_data:
            return sample_data_loader.get_timeseries(entidad or "31")
        
        params = {}
        if entidad:
            params["entidad"] = entidad
        if morbilidad_id:
            params["morbilidad_id"] = morbilidad_id
        if fecha_ini:
            params["fecha_ini"] = fecha_ini
        if fecha_fin:
            params["fecha_fin"] = fecha_fin
        
        r = requests.get(
            f"{self.base_url}/api/v1/timeseries",
            params=params,
            timeout=TIMEOUT
        )
        r.raise_for_status()
        return r.json()
    
    def get_map_data(self) -> Dict[str, Any]:
        """Get map data by entity."""
        if self.use_sample_data:
            return {"entidades": [], "message": "Sample data mode"}
        r = requests.get(f"{self.base_url}/api/v1/map/entidad", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    
    def get_alerts(self, estado: str = "activa") -> Dict[str, Any]:
        """Get alerts."""
        if self.use_sample_data:
            return sample_data_loader.get_alerts()
        r = requests.get(
            f"{self.base_url}/api/v1/alerts",
            params={"estado": estado},
            timeout=TIMEOUT
        )
        r.raise_for_status()
        return r.json()
    
    def submit_survey(self, survey_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit clinical survey."""
        if self.use_sample_data:
            return {"status": "success", "mode": "sample_data"}
        r = requests.post(
            f"{self.base_url}/api/v1/survey",
            json=survey_data,
            timeout=TIMEOUT
        )
        r.raise_for_status()
        return r.json()


# Global client instance
api_client = EpiscopioAPIClient()
