"""Episcopio API - FastAPI application.

Endpoint families:

* ``/api/v1/status|health|meta`` — service metadata.
* ``/api/v1/session/*`` — server-side credential vault: a browser holds only an
  opaque session id, never the keys themselves.
* ``/api/v1/pipeline/*`` — start a run for a session and poll its progress.
* ``/api/v1/kpi|timeseries|alerts|map`` — read the session's ingested data,
  falling back to bundled sample data when the session has not run anything.

Every request that touches a session carries its id in the ``X-Episcopio-Session``
header. Session ids are 256-bit random values minted server-side; there is no
cross-session read path, which is what the previous global-client design lacked.
"""
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Literal, Optional
import logging
import sys
import os

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.security import RateLimitMiddleware, SecurityHeadersMiddleware  # noqa: E402
from config.loader import load_config  # noqa: E402
from core.datastore import data_store  # noqa: E402
from core.runs import run_registry  # noqa: E402
from core.vault import SessionExpired, vault  # noqa: E402
from ingesta.oficial import verificar_fuentes  # noqa: E402
from ingesta.providers import describe_providers, get_provider  # noqa: E402
from orchestrator.pipeline import start_run  # noqa: E402

logger = logging.getLogger(__name__)

app_settings, alert_settings, secrets, api_settings, session_settings = load_config()

# Align the vault's limits with the deployment's configuration.
vault.ttl_seconds = session_settings.credential_ttl_minutes * 60
vault.max_sessions = session_settings.max_sessions

app = FastAPI(
    title=api_settings.title,
    description=api_settings.description,
    version=app_settings.version,
    # Interactive docs are useful in development but are an unnecessary
    # surface on a public production deployment.
    docs_url=None if app_settings.is_production else "/docs",
    redoc_url=None if app_settings.is_production else "/redoc",
    openapi_url=None if app_settings.is_production else "/openapi.json",
)

if not app_settings.is_production:
    weak = secrets.has_placeholder_secrets()
    if weak:
        logger.warning(
            "Ejecutando con secretos de ejemplo (%s). Configúrelos antes de desplegar.",
            ", ".join(weak),
        )

app.add_middleware(
    SecurityHeadersMiddleware,
    https_only=app_settings.is_production,
)
app.add_middleware(
    RateLimitMiddleware,
    read_limit=api_settings.rate_limit_per_minute,
    write_limit=api_settings.write_rate_limit_per_minute,
)

# CORS: the loader has already rejected a credentialed wildcard in production,
# and the method/header lists are explicit rather than "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=secrets.cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Episcopio-Session"],
    max_age=600,
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

ENTIDAD_PATTERN = r"^\d{2}$"
FECHA_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


class KPIRequest(BaseModel):
    """Request model for KPI endpoint."""
    entidad: Optional[str] = Field(None, pattern=ENTIDAD_PATTERN, description="Clave de entidad (2 dígitos)")
    morbilidad_id: Optional[int] = Field(None, ge=1, le=9999)
    fecha_ini: Optional[str] = Field(None, pattern=FECHA_PATTERN)
    fecha_fin: Optional[str] = Field(None, pattern=FECHA_PATTERN)


class SurveyRequest(BaseModel):
    """Request model for the anonymous clinical survey."""
    cve_ent: str = Field(..., pattern=ENTIDAD_PATTERN, description="Clave de entidad (2 dígitos)")
    cve_mun: Optional[str] = Field(None, pattern=r"^\d{3,5}$")
    sintomas_observacion: str = Field(..., min_length=3, max_length=1000)
    # Literal makes the allowed set part of the schema, so an invalid value is
    # rejected by validation instead of by a hand-written check in the handler.
    nivel_actividad: Literal["bajo", "moderado", "alto"]

    @field_validator("sintomas_observacion")
    @classmethod
    def _strip_observacion(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("La observación no puede estar vacía")
        return cleaned


class CredentialsRequest(BaseModel):
    """Credentials for one provider."""
    provider: str = Field(..., min_length=1, max_length=32)
    credentials: Dict[str, str] = Field(default_factory=dict)

    @field_validator("credentials")
    @classmethod
    def _bound_credentials(cls, v: Dict[str, str]) -> Dict[str, str]:
        if len(v) > 10:
            raise ValueError("Demasiados campos de credencial")
        for key, value in v.items():
            if len(key) > 64 or len(value) > 4096:
                raise ValueError("Campo de credencial fuera de rango")
        return v


# ---------------------------------------------------------------------------
# Session dependency
# ---------------------------------------------------------------------------

def get_session_id(
    x_episcopio_session: Optional[str] = Header(None, alias="X-Episcopio-Session"),
) -> Optional[str]:
    """Extract the session id from the request header, if present."""
    return x_episcopio_session


def require_session(
    session_id: Optional[str] = Depends(get_session_id),
) -> str:
    """Resolve a live session or fail with 401.

    A 401 tells the dashboard to mint a fresh session rather than retry, which
    is the correct response to an expired vault entry.
    """
    if not vault.is_active(session_id):
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")
    return session_id  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Service metadata
# ---------------------------------------------------------------------------

@app.get("/api/v1/status")
def status():
    """Status endpoint with version information."""
    return {
        "app": app_settings.name,
        "version": app_settings.version,
        "environment": app_settings.environment,
        "status": "operational",
        "docs": None if app_settings.is_production else "/docs",
    }


@app.get("/api/v1/health")
def health():
    """Health check endpoint."""
    return {"ok": True, "service": "episcopio-api", "version": app_settings.version}


@app.get("/api/v1/meta")
def meta():
    """Metadata about the available data sources."""
    return {
        "proveedores": describe_providers(),
        "timezone": app_settings.timezone,
        "credential_ttl_minutes": session_settings.credential_ttl_minutes,
    }


@app.get("/api/v1/sources/health")
def sources_health():
    """Live reachability of the public official sources."""
    return {"fuentes": verificar_fuentes()}


# ---------------------------------------------------------------------------
# Session & credentials
# ---------------------------------------------------------------------------

@app.post("/api/v1/session")
def create_session():
    """Mint a session id for a browser to hold."""
    return {"session_id": vault.create_session(), "ttl_minutes": session_settings.credential_ttl_minutes}


@app.get("/api/v1/session/credentials")
def list_credentials(session_id: str = Depends(require_session)):
    """List the session's connected providers, with values redacted."""
    return {
        "connected": vault.connected_providers(session_id),
        "credentials": vault.masked_snapshot(session_id),
    }


@app.post("/api/v1/session/credentials")
def set_credentials(body: CredentialsRequest, session_id: str = Depends(require_session)):
    """Store (or clear) one provider's credentials for this session.

    The response is deliberately redacted: the API never echoes a secret back,
    so a leaked response body cannot disclose a key.
    """
    provider = get_provider(body.provider)
    if provider is None:
        raise HTTPException(status_code=404, detail="Proveedor desconocido.")

    try:
        vault.set_credentials(session_id, body.provider, body.credentials)
    except SessionExpired:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "provider": body.provider,
        "connected": body.provider in vault.connected_providers(session_id),
        "credentials": vault.masked_snapshot(session_id).get(body.provider, {}),
    }


@app.post("/api/v1/session/credentials/validate")
def validate_credentials(body: CredentialsRequest, session_id: str = Depends(require_session)):
    """Check one provider's stored credentials against its live API."""
    provider = get_provider(body.provider)
    if provider is None:
        raise HTTPException(status_code=404, detail="Proveedor desconocido.")

    try:
        stored = vault.get_credentials(session_id, body.provider)
    except SessionExpired:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")

    result = provider.validate(stored or body.credentials)
    return {"provider": body.provider, "ok": result.ok, "status": result.status, "message": result.message}


@app.delete("/api/v1/session")
def destroy_session(session_id: str = Depends(require_session)):
    """Forget a session, its credentials and its data."""
    vault.destroy(session_id)
    data_store.clear(session_id)
    run_registry.clear(session_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

@app.post("/api/v1/pipeline/run")
def run_pipeline(session_id: str = Depends(require_session)):
    """Start an ingest → normalise → analyse run for this session."""
    try:
        run = start_run(session_id)
    except SessionExpired:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada.")
    return run.to_dict()


@app.get("/api/v1/pipeline/status")
def pipeline_status(run_id: Optional[str] = None, session_id: str = Depends(require_session)):
    """Poll the latest (or a specific) run for this session."""
    run = run_registry.get(session_id, run_id) if run_id else run_registry.latest(session_id)
    if run is None:
        return {"status": "idle", "steps": [], "summary": "", "total_records": 0}
    return run.to_dict()


# ---------------------------------------------------------------------------
# Data reads
# ---------------------------------------------------------------------------

def _dataset_or_none(session_id: Optional[str]):
    return data_store.get(session_id) if session_id else None


@app.post("/api/v1/kpi")
def get_kpis(req: KPIRequest, session_id: Optional[str] = Depends(get_session_id)):
    """KPIs for the session's ingested data."""
    dataset = _dataset_or_none(session_id)
    if dataset is None:
        return {"kpis": [], "is_sample": True, "message": "Sin datos ingeridos para esta sesión."}

    entidad = req.entidad or "00"
    kpi = dataset.kpis.get(entidad)
    if kpi is None:
        return {"kpis": [], "is_sample": False, "message": f"Sin datos para la entidad {entidad}."}
    return {"kpis": [kpi], "is_sample": False, "fuentes": dataset.fuentes}


@app.get("/api/v1/timeseries")
def get_timeseries(
    entidad: Optional[str] = None,
    morbilidad_id: Optional[int] = None,
    fecha_ini: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    session_id: Optional[str] = Depends(get_session_id),
):
    """Official and social time series for the session's ingested data."""
    dataset = _dataset_or_none(session_id)
    if dataset is None:
        return {
            "serie_oficial": [],
            "serie_social": {"menciones": []},
            "is_sample": True,
            "message": "Sin datos ingeridos para esta sesión.",
        }

    serie = dataset.serie_oficial
    if fecha_ini:
        serie = [p for p in serie if p["fecha"] >= fecha_ini]
    if fecha_fin:
        serie = [p for p in serie if p["fecha"] <= fecha_fin]

    return {
        "serie_oficial": serie,
        "serie_social": {"menciones": dataset.serie_social},
        "is_sample": False,
        "generated_at": dataset.generated_at,
    }


@app.get("/api/v1/map/entidad")
def get_map_data(session_id: Optional[str] = Depends(get_session_id)):
    """Choropleth data by entity, derived from the session's KPIs."""
    dataset = _dataset_or_none(session_id)
    if dataset is None:
        return {"entidades": [], "is_sample": True}

    entidades = [
        {"cve_ent": ent, "casos": kpi.get("casos_totales", 0), "defunciones": kpi.get("defunciones", 0)}
        for ent, kpi in dataset.kpis.items()
        if ent != "00"
    ]
    return {"entidades": entidades, "is_sample": False}


@app.get("/api/v1/alerts")
def get_alerts(estado: str = "activa", session_id: Optional[str] = Depends(get_session_id)):
    """Alerts raised by the session's most recent run."""
    dataset = _dataset_or_none(session_id)
    if dataset is None:
        return {"alertas": [], "is_sample": True}
    alertas: List[Dict[str, Any]] = [a for a in dataset.alertas if a.get("estado") == estado]
    return {"alertas": alertas, "is_sample": False}


@app.post("/api/v1/survey")
def submit_survey(survey: SurveyRequest, request: Request):
    """Submit an anonymous clinical survey.

    Rate limiting is applied by :class:`RateLimitMiddleware` at the tighter
    write budget, since this is an unauthenticated write path.
    """
    # Persistence lands with the database layer; the endpoint validates and
    # acknowledges without inventing a stored record id.
    logger.info("Sondeo recibido para entidad %s", survey.cve_ent)
    return {
        "success": True,
        "message": "Sondeo recibido. Gracias por tu contribución.",
        "stored": False,
        "detail": "El almacenamiento persistente se habilita al configurar PostgreSQL.",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
