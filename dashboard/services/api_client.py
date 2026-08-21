"""Data access for the Episcopio dashboard.

Two transports, chosen by ``EP_API_URL``:

* **In-process (default).** In the unified deployment the dashboard and the API
  share one process, so the client reads the core services directly. The old
  code instead issued ``requests.get("/api/v1/api/v1/health")`` — a relative URL
  with a duplicated prefix, which ``requests`` cannot send at all. Every "real
  data" call therefore raised, and a blanket ``except`` turned that into a
  blank chart with no explanation.
* **Remote HTTP.** When ``EP_API_URL`` is an absolute ``http(s)`` URL the client
  talks to a separate API host, forwarding the session id as a header.

The client is **stateless with respect to credentials**: every method takes the
caller's ``session_id``. There is no shared mutable key state, so one visitor
can no longer alter what another visitor sees — the defect that made the
previous module-level singleton unsafe on a multi-user server.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from core.datastore import data_store
from core.runs import run_registry
from core.vault import SessionExpired, vault

from .sample_data_loader import sample_data_loader

logger = logging.getLogger(__name__)

SESSION_HEADER = "X-Episcopio-Session"
TIMEOUT = 30


def _resolve_base_url() -> Optional[str]:
    """Return an absolute API base URL, or ``None`` for in-process mode.

    A relative value (``/api/v1``) is not a usable target for ``requests``; it
    signals the unified deployment, where direct calls are both correct and
    faster than looping back through the network stack.
    """
    raw = os.getenv("EP_API_URL", "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return raw.rstrip("/")
    if raw.startswith("/"):
        return None
    logger.warning("EP_API_URL no es una URL absoluta ni una ruta relativa; se ignora.")
    return None


class EpiscopioAPIClient:
    """Session-scoped read/write access to Episcopio data."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url if base_url is not None else _resolve_base_url()

    @property
    def is_remote(self) -> bool:
        return bool(self.base_url)

    # -- transport ---------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        session_id: Optional[str],
        **kwargs: Any,
    ) -> Optional[Dict[str, Any]]:
        """Issue a remote call; returns ``None`` when the API is unreachable."""
        headers = dict(kwargs.pop("headers", {}))
        if session_id:
            headers[SESSION_HEADER] = session_id
        try:
            r = requests.request(
                method, f"{self.base_url}{path}", headers=headers, timeout=TIMEOUT, **kwargs
            )
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            logger.warning("Llamada remota %s %s falló: %s", method, path, type(exc).__name__)
            return None
        except ValueError:
            logger.warning("Respuesta no JSON de %s %s", method, path)
            return None

    # -- sessions ----------------------------------------------------------

    def ensure_session(self, session_id: Optional[str]) -> Optional[str]:
        """Return a live session id, creating one if needed."""
        if self.is_remote:
            if session_id:
                return session_id
            payload = self._request("POST", "/api/v1/session", None)
            return payload.get("session_id") if payload else None
        return vault.ensure_session(session_id)

    def set_credentials(
        self, session_id: str, provider_id: str, credentials: Dict[str, str]
    ) -> bool:
        """Store one provider's credentials. Returns False if the session died."""
        if self.is_remote:
            payload = self._request(
                "POST",
                "/api/v1/session/credentials",
                session_id,
                json={"provider": provider_id, "credentials": credentials},
            )
            return payload is not None
        try:
            vault.set_credentials(session_id, provider_id, credentials)
            return True
        except (SessionExpired, ValueError):
            return False

    def connected_providers(self, session_id: Optional[str]) -> List[str]:
        """Ids of providers this session has credentials for."""
        if not session_id:
            return []
        if self.is_remote:
            payload = self._request("GET", "/api/v1/session/credentials", session_id)
            return list(payload.get("connected", [])) if payload else []
        try:
            return vault.connected_providers(session_id)
        except SessionExpired:
            return []

    # -- pipeline ----------------------------------------------------------

    def start_pipeline(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Trigger a run; returns the initial run state."""
        if self.is_remote:
            return self._request("POST", "/api/v1/pipeline/run", session_id)
        # Imported lazily: the pipeline pulls in every connector, and the
        # dashboard module is imported at app-build time.
        from orchestrator.pipeline import start_run

        try:
            return start_run(session_id).to_dict()
        except SessionExpired:
            return None

    def pipeline_status(self, session_id: Optional[str]) -> Dict[str, Any]:
        """Current run state for this session."""
        idle = {"status": "idle", "steps": [], "summary": "", "total_records": 0}
        if not session_id:
            return idle
        if self.is_remote:
            return self._request("GET", "/api/v1/pipeline/status", session_id) or idle
        run = run_registry.latest(session_id)
        return run.to_dict() if run else idle

    # -- data reads --------------------------------------------------------

    def has_live_data(self, session_id: Optional[str]) -> bool:
        """True when this session has ingested data of its own."""
        if not session_id:
            return False
        if self.is_remote:
            payload = self._request("GET", "/api/v1/timeseries", session_id)
            return bool(payload and not payload.get("is_sample"))
        dataset = data_store.get(session_id)
        return dataset is not None and not dataset.is_empty

    def get_kpis(self, session_id: Optional[str], entidad: str = "00") -> Dict[str, Any]:
        """KPIs for an entity, falling back to sample data."""
        if self.is_remote:
            payload = self._request(
                "POST", "/api/v1/kpi", session_id, json={"entidad": entidad}
            )
            kpis = (payload or {}).get("kpis") or []
            if kpis:
                return kpis[0]
            return sample_data_loader.get_kpis(entidad)

        dataset = data_store.get(session_id)
        if dataset and dataset.kpis.get(entidad):
            return dataset.kpis[entidad]
        return sample_data_loader.get_kpis(entidad)

    def get_timeseries(self, session_id: Optional[str], entidad: str = "31") -> Dict[str, Any]:
        """Official + social series, falling back to sample data."""
        if self.is_remote:
            payload = self._request(
                "GET", "/api/v1/timeseries", session_id, params={"entidad": entidad}
            )
            if payload and not payload.get("is_sample"):
                return payload
            return sample_data_loader.get_timeseries(entidad)

        dataset = data_store.get(session_id)
        if dataset and not dataset.is_empty:
            return dataset.to_dict()
        return sample_data_loader.get_timeseries(entidad)

    def get_alerts(self, session_id: Optional[str]) -> Dict[str, Any]:
        """Active alerts, falling back to sample data."""
        if self.is_remote:
            payload = self._request("GET", "/api/v1/alerts", session_id)
            if payload and not payload.get("is_sample"):
                return payload
            return sample_data_loader.get_alerts()

        dataset = data_store.get(session_id)
        if dataset is not None:
            return {"alertas": dataset.alertas}
        return sample_data_loader.get_alerts()

    def data_source_label(self, session_id: Optional[str]) -> str:
        """Human-readable description of where the current data came from."""
        if self.has_live_data(session_id):
            if not self.is_remote:
                dataset = data_store.get(session_id)
                if dataset and dataset.fuentes:
                    return "Datos en vivo · " + ", ".join(dataset.fuentes)
            return "Datos en vivo"
        return "Datos de muestra"


# One client per process is fine now: it holds no per-user state.
api_client = EpiscopioAPIClient()
