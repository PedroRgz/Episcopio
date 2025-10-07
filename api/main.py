"""Episcopio API - FastAPI application."""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import sys
import os

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.loader import load_config

# Initialize FastAPI app
app_settings, alert_settings, secrets = load_config()

app = FastAPI(
    title="Episcopio API",
    description="API de lectura para monitoreo epidemiológico de México",
    version="1.0.0-mvp"
)

# Configure CORS
origins = secrets.security_cors_allowed_origins.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class KPIRequest(BaseModel):
    """Request model for KPI endpoint."""
    entidad: Optional[str] = Field(None, description="Clave de entidad (2 dígitos)")
    morbilidad_id: Optional[int] = Field(None, description="ID de morbilidad")
    fecha_ini: Optional[str] = Field(None, description="Fecha inicio (YYYY-MM-DD)")
    fecha_fin: Optional[str] = Field(None, description="Fecha fin (YYYY-MM-DD)")


class KPIResponse(BaseModel):
    """Response model for KPI endpoint."""
    entidad: str
    morbilidad: Optional[str]
    casos_totales: int
    defunciones_totales: int
    casos_activos: int
    fecha_actualizacion: str


class TimeSeriesPoint(BaseModel):
    """Time series data point."""
    fecha: str
    casos: int
    defunciones: int


class AlertaResponse(BaseModel):
    """Response model for alerts."""
    id: int
    tipo: str
    regla: str
    estado: str
    created_at: str


class SurveyRequest(BaseModel):
    """Request model for clinical survey."""
    cve_ent: str = Field(..., description="Clave de entidad")
    cve_mun: Optional[str] = Field(None, description="Clave de municipio")
    sintomas_observacion: str = Field(..., description="Observación clínica")
    nivel_actividad: str = Field(..., description="Nivel de actividad: bajo, moderado, alto")


# Endpoints
@app.get("/")
def root():
    """Root endpoint."""
    return {
        "app": app_settings.name,
        "version": app_settings.version,
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/api/v1/health")
def health():
    """Health check endpoint."""
    return {
        "ok": True,
        "service": "episcopio-api",
        "version": app_settings.version
    }


@app.get("/api/v1/meta")
def meta():
    """Metadata about data sources and last update."""
    return {
        "fuentes": [
            "DGE - Dirección General de Epidemiología",
            "INEGI - Instituto Nacional de Estadística y Geografía",
            "CONACYT - Consejo Nacional de Ciencia y Tecnología"
        ],
        "ultima_actualizacion": "2025-01-01T00:00:00Z",
        "timezone": app_settings.timezone
    }


@app.post("/api/v1/kpi")
def get_kpis(req: KPIRequest):
    """
    Get KPIs (Key Performance Indicators) for epidemiological data.
    
    MVP: Returns mock data. Production: Query from PostgreSQL.
    """
    # TODO: Implement database query
    # For MVP, return mock data
    return {
        "kpis": [
            {
                "entidad": req.entidad or "31",
                "morbilidad": "COVID-19",
                "casos_totales": 12500,
                "defunciones_totales": 350,
                "casos_activos": 450,
                "fecha_actualizacion": "2025-01-15"
            }
        ]
    }


@app.get("/api/v1/timeseries")
def get_timeseries(
    entidad: Optional[str] = None,
    morbilidad_id: Optional[int] = None,
    fecha_ini: Optional[str] = None,
    fecha_fin: Optional[str] = None
):
    """
    Get time series data for official and social metrics.
    
    MVP: Returns mock data. Production: Query from PostgreSQL.
    """
    # TODO: Implement database query
    # For MVP, return mock data
    return {
        "serie_oficial": [
            {"fecha": "2025-01-01", "casos": 120, "defunciones": 3},
            {"fecha": "2025-01-08", "casos": 135, "defunciones": 4},
            {"fecha": "2025-01-15", "casos": 145, "defunciones": 5}
        ],
        "serie_social": {
            "menciones": [
                {"fecha": "2025-01-01", "conteo": 45, "sentimiento": -0.1},
                {"fecha": "2025-01-08", "conteo": 52, "sentimiento": -0.3},
                {"fecha": "2025-01-15", "conteo": 68, "sentimiento": -0.4}
            ]
        }
    }


@app.get("/api/v1/map/entidad")
def get_map_data():
    """
    Get choropleth map data by entity.
    
    MVP: Returns mock data. Production: Query from PostgreSQL with PostGIS.
    """
    # TODO: Implement database query with geospatial data
    return {
        "entidades": [
            {"cve_ent": "31", "nombre": "Yucatán", "casos": 1250, "defunciones": 35},
            {"cve_ent": "23", "nombre": "Quintana Roo", "casos": 980, "defunciones": 28},
            {"cve_ent": "04", "nombre": "Campeche", "casos": 650, "defunciones": 18}
        ]
    }


@app.get("/api/v1/alerts")
def get_alerts(estado: Optional[str] = "activa"):
    """
    Get alerts (active or resolved).
    
    MVP: Returns mock data. Production: Query from PostgreSQL.
    """
    # TODO: Implement database query
    return {
        "alertas": [
            {
                "id": 1,
                "tipo": "incremento_subito",
                "regla": "a1",
                "estado": "activa",
                "evidencia": {
                    "entidad": "31",
                    "delta_porcentaje": 25.5,
                    "casos_actual": 145,
                    "casos_promedio": 115
                },
                "created_at": "2025-01-15T10:30:00Z"
            }
        ]
    }


@app.get("/api/v1/bulletin/{bulletin_id}")
def get_bulletin(bulletin_id: int):
    """
    Get rendered bulletin by ID.
    
    MVP: Returns mock data. Production: Query from PostgreSQL.
    """
    # TODO: Implement database query
    if bulletin_id < 1:
        raise HTTPException(status_code=404, detail="Boletín no encontrado")
    
    return {
        "id": bulletin_id,
        "periodo": "2025-01-01 a 2025-01-15",
        "resumen_html": "<h1>Boletín Epidemiológico</h1><p>Resumen del período...</p>",
        "estado": "publicado",
        "published_at": "2025-01-16T00:00:00Z"
    }


@app.post("/api/v1/survey")
def submit_survey(survey: SurveyRequest):
    """
    Submit anonymous clinical survey.
    
    MVP: Validates and returns success. Production: Store in PostgreSQL.
    """
    # TODO: Implement database insert with rate limiting
    # Validate nivel_actividad
    if survey.nivel_actividad not in ["bajo", "moderado", "alto"]:
        raise HTTPException(
            status_code=400,
            detail="nivel_actividad debe ser: bajo, moderado, o alto"
        )
    
    return {
        "success": True,
        "message": "Sondeo registrado exitosamente. Gracias por tu contribución.",
        "id": 12345  # Mock ID
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
