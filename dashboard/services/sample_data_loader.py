"""Sample data loader for Episcopio dashboard."""
import json
import os
from typing import Dict, Any


class SampleDataLoader:
    """Loader for sample data."""
    
    def __init__(self):
        """Initialize the sample data loader."""
        self.data_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            "sample_data.json"
        )
        self._data = None
        self._load_data()
    
    def _load_data(self):
        """Load sample data from JSON file."""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
        except Exception as e:
            print(f"Error loading sample data: {e}")
            self._data = self._get_empty_data()
    
    def _get_empty_data(self) -> Dict[str, Any]:
        """Return empty data structure."""
        return {
            "meta": {
                "description": "No sample data available",
                "is_sample": True
            },
            "kpis": {},
            "timeseries": {},
            "alerts": []
        }
    
    def get_kpis(self, entidad: str) -> Dict[str, Any]:
        """Get KPIs for an entity."""
        return self._data.get("kpis", {}).get(entidad, {
            "casos_totales": 0,
            "casos_activos": 0,
            "defunciones": 0,
            "variacion_casos": 0,
            "variacion_activos": 0,
            "variacion_defunciones": 0
        })
    
    def get_timeseries(self, entidad: str) -> Dict[str, Any]:
        """Get time series data for an entity."""
        return self._data.get("timeseries", {}).get(entidad, {
            "serie_oficial": [],
            "serie_social": {"menciones": []}
        })
    
    def get_alerts(self) -> Dict[str, Any]:
        """Get alerts."""
        return {
            "alertas": self._data.get("alerts", [])
        }
    
    def is_sample_data(self) -> bool:
        """Check if this is sample data."""
        return self._data.get("meta", {}).get("is_sample", True)


# Global instance
sample_data_loader = SampleDataLoader()
