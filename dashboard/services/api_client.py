"""API client for Episcopio dashboard."""
import requests
import os
from typing import Optional, Dict, Any


BASE_URL = os.getenv("EP_API_URL", "http://api:8000")
TIMEOUT = 30


class EpiscopioAPIClient:
    """Client for Episcopio API."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")
    
    def health(self) -> Dict[str, Any]:
        """Check API health."""
        r = requests.get(f"{self.base_url}/api/v1/health", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    
    def get_meta(self) -> Dict[str, Any]:
        """Get metadata about data sources."""
        r = requests.get(f"{self.base_url}/api/v1/meta", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    
    def get_kpis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get KPIs."""
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
        r = requests.get(f"{self.base_url}/api/v1/map/entidad", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    
    def get_alerts(self, estado: str = "activa") -> Dict[str, Any]:
        """Get alerts."""
        r = requests.get(
            f"{self.base_url}/api/v1/alerts",
            params={"estado": estado},
            timeout=TIMEOUT
        )
        r.raise_for_status()
        return r.json()
    
    def submit_survey(self, survey_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit clinical survey."""
        r = requests.post(
            f"{self.base_url}/api/v1/survey",
            json=survey_data,
            timeout=TIMEOUT
        )
        r.raise_for_status()
        return r.json()


# Global client instance
api_client = EpiscopioAPIClient()
