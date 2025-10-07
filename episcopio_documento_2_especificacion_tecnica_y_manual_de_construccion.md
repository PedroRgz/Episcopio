# Episcopio — Documento 2: Especificación Técnica y Manual de Construcción

> **Propósito**: documento técnico ejecutable por un asistente de IA (IA Builder) para construir el MVP y la V1 de **Episcopio** siguiendo prácticas 12‑Factor. Incluye: estructura de repos, contratos de datos, APIs, pipelines, seguridad, CI/CD e instrucciones locales. Integra los archivos y listas que compartiste (fuentes oficiales, redes sociales, tecnologías) y define un **sistema unificado de llaves/API** mediante un documento central.

---

## 0) Resumen de arquitectura

**Estilo**: modular por dominio + servicios livianos.

- **Ingesta** (`ingesta/`): conectores a fuentes oficiales y sociales; scraping ligero de boletines (PDF/HTML).  
- **Normalización/ETL** (`etl/`): limpieza, estandarización de fechas, claves geo (INEGI), catálogos.  
- **Persistencia** (`db/`): PostgreSQL + PostGIS; colección NoSQL para sociales (opcional).  
- **Analítica** (`analytics/`): KPIs, sentimiento, correlación oficial–social, reglas de alertas.  
- **API de lectura** (`api/`): FastAPI, endpoints versionados.  
- **Dashboard** (`dashboard/`): Dash/Plotly (MVP) con plan de migración a React/Leaflet.  
- **Orquestación** (`orchestrator/`): Airflow/Prefect o `cron` + Papermill para MVP.  
- **Observabilidad** (`ops/`): logging, métricas, trazas, QA de datos.

---

## 1) Estructura de repositorios (monorepo sugerido)

```
episcopio/
├─ api/                      # FastAPI: endpoints de lectura
├─ analytics/                # cálculos de KPIs, sentimiento, correlación, alertas
├─ dashboard/                # app Dash/Plotly (MVP)
├─ db/
│  ├─ migrations/            # alembic + SQL/DDL
│  ├─ seeds/                 # datos semilla (catálogos, claves INEGI)
│  └─ schema/                # DBML, diccionario de datos
├─ etl/                      # transformaciones y normalizadores
├─ ingesta/                  # conectores oficiales/sociales y scrapers
├─ orchestrator/             # Airflow/Prefect/Papermill jobs
├─ ops/                      # observabilidad, dashboards Prometheus/Grafana
├─ config/
│  ├─ settings.yaml          # config no sensible
│  ├─ secrets.sample.yaml    # **plantilla** de llaves/API
│  └─ secrets.local.yaml     # **documento único** que editas con tus llaves
├─ infra/                    # Docker, docker-compose, IaC opcional (Terraform)
├─ tests/                    # unitarias, integración, contrato API
└─ README.md
```

> **Monorepo** simplifica CI/CD inicial. Si prefieres repos separados, replica la misma estructura por servicio.

---

## 2) Gestión de configuración y **llaves/API desde un documento**

### 2.1 Archivos de configuración

- `config/settings.yaml` (en repo): parámetros no sensibles (rutas, ventanas, umbrales).  
- `config/secrets.sample.yaml` (en repo): **plantilla** con todas las llaves/credenciales necesarias.  
- `config/secrets.local.yaml` (fuera del control de versiones o encriptado): **documento único que editas** pegando tus llaves reales.  
- Variables de entorno **tienen prioridad** sobre cualquier YAML.

#### `config/secrets.sample.yaml` (ejemplo)
```yaml
# Copia este archivo a secrets.local.yaml y completa tus llaves
postgres:
  user: "episcopio"
  password: "<TU_PASSWORD>"
  host: "db"
  port: 5432
  database: "episcopio"
redis:
  url: "redis://redis:6379/0"
apis:
  inegi:
    token: "INEGI_TOKEN"
  twitter:
    bearer_token: "TW_BEARER"
  facebook:
    app_id: "FB_APP_ID"
    app_secret: "FB_APP_SECRET"
    access_token: "FB_ACCESS_TOKEN"
  instagram:
    app_id: "IG_APP_ID"
    app_secret: "IG_APP_SECRET"
    access_token: "IG_ACCESS_TOKEN"
  reddit:
    client_id: "REDDIT_CLIENT"
    client_secret: "REDDIT_SECRET"
    user_agent: "episcopio/1.0"
  newsapi:
    key: "NEWS_API_KEY"
security:
  jwt_secret: "CAMBIA_ESTE_SECRETO"
  cors_allowed_origins: ["https://episcopio.mx", "http://localhost:8050"]
```

#### Carga de configuración en Python (Pydantic + YAML)
```python
# config/loader.py
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import yaml, os

class AppSettings(BaseModel):
    timezone: str = "America/Merida"
    alert_windows_days: int = 14

class Secrets(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_database: str = "episcopio"
    redis_url: str = "redis://redis:6379/0"
    apis_inegi_token: str | None = None
    apis_twitter_bearer_token: str | None = None
    # ... demás llaves

    class Config:
        env_prefix = "EP_"          # p.ej., EP_POSTGRES_USER
        env_file = ".env"           # opcional para desarrollo


def load_config():
    with open("config/settings.yaml", "r", encoding="utf-8") as f:
        static_cfg = yaml.safe_load(f)
    # secrets.local.yaml es opcional si usas solo variables de entorno
    secrets_path = "config/secrets.local.yaml"
    secrets_yaml = {}
    if os.path.exists(secrets_path):
        with open(secrets_path, "r", encoding="utf-8") as f:
            secrets_yaml = yaml.safe_load(f) or {}

    # Variables de entorno tienen prioridad: Pydantic las toma si existen
    s = Secrets(**flatten_yaml_keys(secrets_yaml))
    a = AppSettings(**static_cfg.get("app", {}))
    return a, s

# util: aplana claves anidadas a formato pydantic (apis.twitter.bearer_token -> apis_twitter_bearer_token)
def flatten_yaml_keys(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in (d or {}).items():
        key = (prefix + "_" + k) if prefix else k
        if isinstance(v, dict):
            out.update(flatten_yaml_keys(v, key))
        else:
            out[key.replace(".", "_")] = v
    return out
```

> Con esto, **tu único paso manual** es editar `config/secrets.local.yaml` (o usar variables de entorno) y el sistema leerá las llaves. Agrega `config/secrets.local.yaml` a `.gitignore`.

---

## 3) Modelo de datos (PostgreSQL + PostGIS)

### 3.1 Esquema relacional

- `geo_entidad` *(catálogo)*: clave INEGI (2 dígitos), nombre, geometría (MULTIPOLYGON).  
- `geo_municipio` *(catálogo)*: clave INEGI (5 dígitos), FK entidad, geometría.  
- `morbilidad` *(catálogo)*: código/UM (si disponible), nombre normalizado, tipo (transmisible/no).  
- `serie_oficial` *(hechos)*: fecha/semana ISO, fk_entidad/municipio, fk_morbilidad, casos, defunciones, fuente, versionado.  
- `social_menciones` *(hechos)*: fecha/hora, plataforma, texto_hash, geo (opcional), relevancia (0/1), sentimiento (-1..1), conteos por ventana, enlace a original (si permitido).  
- `sondeo_clinico` *(hechos)*: fecha/hora, fk_entidad/municipio, campos breves (síntomas/observación), **sin PII**.  
- `alerta` *(eventos)*: id, tipo, regla, parámetros, evidencia (serie/resumen), estado, timestamps.  
- `boletin` *(documentos)*: id, periodo, resumen HTML/MD, adjuntos, versión.  
- `qa_evento` *(operación)*: chequeos de datos (schema, ranges, freshness), resultado, severidad.  
- `ingesta_log` *(operación)*: fuente, ventana, filas, duración, errores.

#### DDL principal (extracto)
```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE geo_entidad (
  cve_ent CHAR(2) PRIMARY KEY,
  nombre  TEXT NOT NULL,
  geom    GEOMETRY(MULTIPOLYGON, 4326)
);

CREATE TABLE morbilidad (
  id SERIAL PRIMARY KEY,
  codigo TEXT,
  nombre TEXT NOT NULL,
  tipo   TEXT CHECK (tipo IN ('transmisible','no_transmisible'))
);

CREATE TABLE serie_oficial (
  id BIGSERIAL PRIMARY KEY,
  fecha DATE NOT NULL,
  semana_iso INT NOT NULL,
  cve_ent CHAR(2) REFERENCES geo_entidad(cve_ent),
  cve_mun CHAR(5),
  morbilidad_id INT REFERENCES morbilidad(id),
  casos INT DEFAULT 0,
  defunciones INT DEFAULT 0,
  fuente TEXT NOT NULL,
  version INT DEFAULT 1,
  UNIQUE (fecha, cve_ent, cve_mun, morbilidad_id, fuente)
);

CREATE TABLE social_menciones (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMP WITH TIME ZONE NOT NULL,
  plataforma TEXT NOT NULL,
  texto_hash CHAR(64) NOT NULL,
  cve_ent CHAR(2),
  cve_mun CHAR(5),
  relevancia BOOLEAN,
  sentimiento NUMERIC(4,3),
  conteo INT DEFAULT 1,
  url TEXT,
  UNIQUE (plataforma, texto_hash)
);

CREATE TABLE alerta (
  id BIGSERIAL PRIMARY KEY,
  tipo TEXT NOT NULL,
  regla TEXT NOT NULL,
  parametros JSONB NOT NULL,
  evidencia JSONB,
  estado TEXT CHECK (estado IN ('activa','resuelta')) DEFAULT 'activa',
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### 3.2 DBML para diagrama
```dbml
Table geo_entidad {
  cve_ent char(2) [pk]
  nombre text
}

Table morbilidad {
  id int [pk, increment]
  codigo text
  nombre text
  tipo text
}

Table serie_oficial {
  id bigint [pk, increment]
  fecha date
  semana_iso int
  cve_ent char(2) [ref: > geo_entidad.cve_ent]
  cve_mun char(5)
  morbilidad_id int [ref: > morbilidad.id]
  casos int
  defunciones int
  fuente text
  version int
}

Table social_menciones {
  id bigint [pk, increment]
  ts timestamp
  plataforma text
  texto_hash char(64)
  cve_ent char(2)
  cve_mun char(5)
  relevancia bool
  sentimiento decimal(4,3)
  conteo int
  url text
}

Table alerta {
  id bigint [pk, increment]
  tipo text
  regla text
  parametros jsonb
  evidencia jsonb
  estado text
  created_at timestamp
}
```

---

## 4) Contratos de datos y diccionario

**Claves geo**: INEGI (`cve_ent` 2 dígitos, `cve_mun` 5 dígitos).  
**Fechas**: ISO‑8601; semana ISO para agregados (lunes‑domingo).  
**Sentimiento**: escala -1..1 (NLTK/VADER base).  
**Relevancia social**: clasificador binario (reglas + modelo sencillo).  
**Versionado**: `version` por lote de fuente; conservar historial si cambia la cifra oficial.

---

## 5) Ingesta y ETL

### 5.1 Conectores oficiales (según tu CSV)
- SINAVE / SUAVE — autenticación; scraping de boletines si aplica.  
- INEGI API — indicadores demográficos/socioeconómicos.  
- Datos Abiertos SSA / DGE — CSV/Excel (COVID, anuarios).  
- CONACYT COVID — JSON/CSV.

### 5.2 Conectores sociales (según tu CSV)
- Twitter/X (OAuth2, límites de cuota).  
- Facebook Graph e Instagram Basic (datos públicos básicos).  
- Reddit API (subreddits salud).  
- NewsAPI (noticias).  
> Respetar Términos y robots.txt. No recolectar PII.

### 5.3 Orquestación (Airflow ejemplo)
```python
# orchestrator/dags/episcopio_mvp.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from ingesta.oficial import fetch_dge, fetch_inegi
from etl.normaliza import normalizar_dge
from analytics.kpis import recalcular_kpis
from analytics.alertas import evaluar_alertas

with DAG(
    dag_id="episcopio_mvp",
    start_date=datetime(2025, 1, 1),
    schedule_interval="0 */6 * * *",  # cada 6 horas
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=10)},
) as dag:
    dge = PythonOperator(task_id="fetch_dge", python_callable=fetch_dge)
    inegi = PythonOperator(task_id="fetch_inegi", python_callable=fetch_inegi)
    norm = PythonOperator(task_id="normalizar_dge", python_callable=normalizar_dge)
    kpis = PythonOperator(task_id="recalcular_kpis", python_callable=recalcular_kpis)
    alrt = PythonOperator(task_id="evaluar_alertas", python_callable=evaluar_alertas)

    [dge, inegi] >> norm >> kpis >> alrt
```

### 5.4 Papermill/cron (alternativa MVP ligera)
- Programar `papermill` sobre `dashboard_epidemiologico_notebook.ipynb` para generar tablas y gráficos de salida reutilizables.  
- `cron` en zona horaria **America/Merida**.

### 5.5 Limpieza y normalización
- Estandarizar columnas (`fecha`, `cve_ent`, `cve_mun`, `morbilidad_id`, `casos`, `defunciones`).  
- Deduplicación por (`fecha`,`entidad/mun`,`morbilidad`,`fuente`).  
- Conversión de PDFs a tablas (tabula/camelot); loggear calidad OCR.

### 5.6 Calidad de datos (Great Expectations o validadores propios)
- **Schema**: tipos, no nulos.  
- **Rangos**: `casos >= 0`, `defunciones >= 0`.  
- **Freshness**: última fecha por entidad ≤ 72h para oficial.  
- **Densidad temporal**: sin huecos > 2 semanas.

---

## 6) Analítica, reglas y alertas

### 6.1 KPIs y tiempos
- Ventanas móviles 7/14/28 días; tasas por 100k (INEGI como denominador).  
- Cruces oficial–social (correlación Spearman por ventana).  

### 6.2 Reglas (YAML declarativo)
```yaml
# analytics/reglas/alertas.yaml
- id: a1
  nombre: "Incremento súbito oficial"
  serie: "casos"
  ventana_ref: 14
  umbral_delta: 0.2       # +20% vs media móvil
  min_casos: 5
- id: a2
  nombre: "Pico social + negativo"
  serie: "menciones"
  zscore: 2.0
  sentimiento_max: -0.2
```

### 6.3 Evaluador de reglas (esqueleto)
```python
# analytics/alertas.py
import yaml, pandas as pd

def evaluar_alertas(kpis_df):
    reglas = yaml.safe_load(open("analytics/reglas/alertas.yaml"))
    activas = []
    for r in reglas:
        # filtra serie y calcula condiciones; añade evidencia
        pass
    # inserta en tabla alerta; registra evidencia JSON
```

---

## 7) API de lectura (FastAPI)

### 7.1 Endpoints (v1)
- `GET /api/v1/health` → estado breve.  
- `GET /api/v1/meta` → fuentes, última actualización.  
- `GET /api/v1/kpi` → KPIs por entidad/fecha/morbilidad.  
- `GET /api/v1/timeseries` → serie oficial/social agregada.  
- `GET /api/v1/map/entidad` → valores por entidad (choropleth).  
- `GET /api/v1/alerts` → alertas activas/periodo.  
- `GET /api/v1/bulletin/{id}` → boletín renderizado.  
- `POST /api/v1/survey` → registrar entrada de **sondeo anónimo** (ratelimited).

### 7.2 Esqueleto
```python
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from config.loader import load_config

app = FastAPI(title="Episcopio API", version="1.0")
app.state.cfg, app.state.secrets = load_config()

class KPIRequest(BaseModel):
    entidad: str | None = None  # cve_ent
    morbilidad_id: int | None = None
    fecha_ini: str | None = None
    fecha_fin: str | None = None

@app.get("/api/v1/health")
def health():
    return {"ok": True}

@app.post("/api/v1/kpi")
def kpi(req: KPIRequest):
    # consulta agregados en Postgres
    return {"kpis": []}
```

### 7.3 Seguridad
- CORS cerrado, lista blanca desde `config`.  
- Rate‑limit (ej. 60 rps por IP).  
- Endpoints admin protegidos con JWT (clave en `security.jwt_secret`).

---

## 8) Dashboard (Dash/Plotly, MVP)

- Consumir **API de lectura** (evitar conexión directa a DB en el cliente).  
- Reutilizar tu `dashboard_epidemiologico_ejemplo.py` como base: KPIs, timeseries, mapa.  
- Estilos: layout liviano, tarjetas KPI, selector de entidad/morbilidad, rango de fechas, gráfico de sentimiento y feed de alertas.

```
dashboard/
├─ app.py
├─ components/
├─ assets/
└─ services/api_client.py
```

**`services/api_client.py`**
```python
import requests, os
BASE_URL = os.getenv("EP_API_URL", "http://api:8000")

def get_kpis(payload):
    r = requests.post(f"{BASE_URL}/api/v1/kpi", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()
```

---

## 9) Seguridad, privacidad y cumplimiento

- **PII**: no almacenar nombres/IDs; sondeo anónimo; hashes de texto para deduplicar.  
- **Geolocalización**: redondeo/obfuscación; almacenamiento a nivel entidad/municipio.  
- **Retención**: logs con TTL; rotación de llaves.  
- **Auditoría**: bitácora de accesos; versionado de reglas.

---

## 10) Observabilidad y QA

- **Logging**: JSON estructurado (uvicorn, workers, ETL).  
- **Métricas**: Prometheus (latencia API, errores, frescura de datos).  
- **Trazas**: OpenTelemetry (opcional).  
- **QA de datos**: tablero de *freshness* y densidad; tabla `qa_evento`.

---

## 11) Despliegue (Docker Compose, MVP)

**`infra/docker-compose.yml`**
```yaml
version: "3.9"
services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: episcopio
      POSTGRES_USER: ${EP_POSTGRES_USER:-episcopio}
      POSTGRES_PASSWORD: ${EP_POSTGRES_PASSWORD:-changeme}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  api:
    build: ./api
    environment:
      EP_POSTGRES_USER: ${EP_POSTGRES_USER}
      EP_POSTGRES_PASSWORD: ${EP_POSTGRES_PASSWORD}
      EP_POSTGRES_HOST: db
      EP_POSTGRES_DATABASE: episcopio
    depends_on: [db]
    ports: ["8000:8000"]

  dashboard:
    build: ./dashboard
    environment:
      EP_API_URL: http://api:8000
    depends_on: [api]
    ports: ["8050:8050"]

  scheduler:
    build: ./orchestrator
    depends_on: [api, db]

volumes:
  pgdata:
```

> Puedes montar `config/secrets.local.yaml` como volumen de solo lectura en `api`/`scheduler`.

---

## 12) CI/CD (GitHub Actions ejemplo)

**`.github/workflows/ci.yml`**
```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: pytest -q
  docker:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          push: true
          tags: tuusuario/episcopio-api:latest
```

---

## 13) Rendimiento y SLOs

- **API**: P95 < 400 ms (lecturas agregadas), error rate < 1%.  
- **Dashboard**: carga inicial < 3 s; interacciones < 1 s con cache Redis.  
- **Pipelines**: actualizaciones oficiales < 24 h; sociales en cuasi‑tiempo real si la cuota lo permite.

---

## 14) Seguridad de acceso y roles

- **Anónimo**: lectura pública de agregados.  
- **Administrador**: gestión de reglas y boletines (JWT).  
- **Clave de API** (opcional): para integradores externos con `X-API-Key` y *rate limit*.

---

## 15) Pruebas

- **Unitarias**: transformaciones ETL, parsers PDF/CSV, clasificadores.  
- **Integración**: endpoints API contra base de prueba.  
- **Contrato**: OpenAPI validada en CI.  
- **E2E**: dashboard consumiendo API en entorno efímero.

---

## 16) Guía rápida para correr en local

1. Clona `episcopio/` y copia `config/secrets.sample.yaml` → `config/secrets.local.yaml`; rellena llaves (o usa variables `EP_*`).  
2. `docker compose up -d --build` (levanta db, api, dashboard).  
3. Corre ingestas con `make ingest` o espera al *scheduler*.  
4. Abre `http://localhost:8050` (dashboard) y `http://localhost:8000/docs` (API).  
5. Zona horaria por defecto: **America/Merida** (configurable en `settings.yaml`).

---

## 17) Anexos (a partir de tus archivos CSV)

### 17.1 Fuentes oficiales

- **Fuente**: SINAVE - Sistema Nacional de Vigilancia Epidemiológica; **URL/Endpoint**: https://www.sinave.gob.mx; **Tipo_Datos**: Casos notificación obligatoria, brotes, emergencias; **Formato**: API/Web (requiere autenticación)
- **Fuente**: API INEGI - Banco de Indicadores; **URL/Endpoint**: https://www.inegi.org.mx/servicios/api_indicadores.html; **Tipo_Datos**: Indicadores socioeconómicos, demográficos por municipio; **Formato**: JSON, XML
- **Fuente**: Datos Abiertos SSA - Dirección General de Epidemiología; **URL/Endpoint**: https://www.gob.mx/salud/documentos/datos-abiertos-152127; **Tipo_Datos**: Bases datos COVID-19, anuarios morbilidad 2015-2017; **Formato**: CSV, Excel
- **Fuente**: Dashboard COVID-19 CONACYT; **URL/Endpoint**: https://datos.covid-19.conacyt.mx; **Tipo_Datos**: Datos georreferenciados COVID-19 en tiempo real; **Formato**: JSON, CSV
- **Fuente**: SUAVE - Sistema Único Automatizado para Vigilancia Epidemiológica; **URL/Endpoint**: Sistema integrado en SINAVE; **Tipo_Datos**: Casos nuevos enfermedades transmisibles/no transmisibles; **Formato**: Integrado con SINAVE

### 17.2 Fuentes redes/noticias

- **Plataforma**: Twitter/X API; **Endpoint/Método**: API v2 con autenticación OAuth 2.0; **Datos_Recolectados**: Tweets con síntomas, geolocalización, hashtags salud; **Limitaciones**: Límites de requests, acceso de pago para investigación
- **Plataforma**: Facebook Graph API; **Endpoint/Método**: Graph API v18.0; **Datos_Recolectados**: Posts públicos, reacciones, comentarios; **Limitaciones**: Acceso limitado tras cambios política 2022
- **Plataforma**: Instagram Basic Display API; **Endpoint/Método**: Basic Display API; **Datos_Recolectados**: Posts con hashtags relacionados salud; **Limitaciones**: Solo datos básicos, requiere aprobación
- **Plataforma**: Reddit API; **Endpoint/Método**: Reddit API (OAuth); **Datos_Recolectados**: Discusiones subreddits médicos/salud; **Limitaciones**: Límites de requests por minuto
- **Plataforma**: Google News API; **Endpoint/Método**: News API; **Datos_Recolectados**: Noticias brotes, emergencias sanitarias; **Limitaciones**: Requiere API key, límites por día

### 17.3 Tecnologías sugeridas

- **Categoría**: Recolección Datos; **Tecnología**: Python Requests; **Propósito**: APIs REST, web scraping automatizado
- **Categoría**: Recolección Datos; **Tecnología**: Tweepy, Facebook SDK; **Propósito**: Conexión APIs redes sociales
- **Categoría**: Procesamiento ETL; **Tecnología**: Pandas, NumPy; **Propósito**: Limpieza, transformación, normalización datos
- **Categoría**: Procesamiento ETL; **Tecnología**: Apache Airflow; **Propósito**: Orquestación pipelines datos automatizados
- **Categoría**: Análisis Datos; **Tecnología**: Scikit-learn, NLTK; **Propósito**: NLP análisis sentimientos, ML detección patrones
- **Categoría**: Visualización; **Tecnología**: Plotly/Seaborn/Matplotlib; **Propósito**: Gráficos interactivos y estáticos
- **Categoría**: Geoespacial; **Tecnología**: GeoPandas, Folium, PostGIS; **Propósito**: Mapas, joins espaciales
- **Categoría**: Almacenamiento; **Tecnología**: PostgreSQL, MongoDB; **Propósito**: Relacional + no relacional para sociales
- **Categoría**: Frontend Dashboard; **Tecnología**: Dash/Plotly (MVP), React/Leaflet (V1); **Propósito**: UI rápida, migración a SPA
- **Categoría**: DevOps; **Tecnología**: Docker, Docker Compose; **Propósito**: Empaquetado y despliegue reproducible
- **Categoría**: Orquestación ligera; **Tecnología**: Papermill + cron; **Propósito**: Ejecución notebooks programada
- **Categoría**: Observabilidad; **Tecnología**: Prometheus, Grafana, OpenTelemetry; **Propósito**: Métricas, trazas y dashboards operativos

---

## 18) Roadmap técnico MVP → V1

- **MVP**: conectores DGE/INEGI, tablas básicas, API lectura, dashboard KPIs/serie/mapa, reglas A1/A2, boletín HTML.  
- **V1**: filtros municipales/edades, CUSUM/STL, API pública con claves, exportación PDF, i18n, panel QA datos.

---

## 19) Notas de implementación con tus scripts/notebook

- Usa `dashboard_epidemiologico_ejemplo.py` como base del front Dash; re‑enrutar peticiones a `api_client`.  
- Con `dashboard_epidemiologico_notebook.ipynb` y Papermill, genera *artefactos* (CSV/HTML) que el dashboard puede consumir mientras se estabiliza la API.  
- Integra `script.py`/`script_1.py` como conectores/seeders iniciales en `ingesta/` y `db/seeds/`.

---

### Fin del Documento 2

