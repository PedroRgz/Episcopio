# Arquitectura de Episcopio MVP

## Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FUENTES DE DATOS                           │
├───────────────────────────┬─────────────────────────────────────────┤
│      Oficiales            │           Sociales                      │
│  - DGE/SINAVE             │  - Twitter/X API                        │
│  - INEGI API              │  - Facebook Graph API                   │
│  - Datos Abiertos SSA     │  - Reddit API                           │
│  - CONACYT COVID-19       │  - News API                             │
└───────────┬───────────────┴───────────────┬─────────────────────────┘
            │                               │
            │                               │
            ▼                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│                       CAPA DE INGESTA                                 │
├───────────────────────────────────────────────────────────────────────┤
│  ingesta/                                                             │
│  ├─ oficial.py    - Conectores a fuentes oficiales                   │
│  └─ social.py     - Conectores a redes sociales                      │
│                                                                       │
│  Funciones:                                                           │
│  - Descarga de datos de APIs y archivos                              │
│  - Parsing de CSV/Excel/JSON/PDF                                     │
│  - Clasificación de relevancia                                       │
│  - Análisis de sentimiento básico                                    │
└───────────────────────────────┬───────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────┐
│                          CAPA ETL                                     │
├───────────────────────────────────────────────────────────────────────┤
│  etl/                                                                 │
│  └─ normaliza.py  - Transformaciones y limpieza                      │
│                                                                       │
│  Funciones:                                                           │
│  - Estandarización de fechas (ISO-8601)                              │
│  - Normalización de códigos INEGI                                    │
│  - Mapeo de nombres de morbilidades                                  │
│  - Cálculo de semanas ISO                                            │
│  - Validación de datos                                               │
│  - Deduplicación                                                     │
└───────────────────────────────┬───────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────┐
│                      CAPA DE PERSISTENCIA                             │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────┐    ┌────────────────────────┐  │
│  │   PostgreSQL + PostGIS          │    │      Redis             │  │
│  │   (Base de datos relacional)    │    │      (Cache)           │  │
│  ├─────────────────────────────────┤    └────────────────────────┘  │
│  │  - geo_entidad                  │                                │
│  │  - geo_municipio                │                                │
│  │  - morbilidad                   │                                │
│  │  - serie_oficial                │                                │
│  │  - social_menciones             │                                │
│  │  - sondeo_clinico               │                                │
│  │  - alerta                       │                                │
│  │  - boletin                      │                                │
│  │  - qa_evento                    │                                │
│  │  - ingesta_log                  │                                │
│  └─────────────────────────────────┘                                │
│                                                                       │
└───────────────────────┬───────────────────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────────────────┐
│                       CAPA DE ANALÍTICA                               │
├───────────────────────────────────────────────────────────────────────┤
│  analytics/                                                           │
│  ├─ kpis.py       - Cálculo de indicadores                           │
│  ├─ alertas.py    - Evaluación de reglas                             │
│  └─ reglas/                                                           │
│     └─ alertas.yaml - Configuración de reglas                        │
│                                                                       │
│  Funciones:                                                           │
│  - KPIs por entidad/morbilidad                                       │
│  - Promedios móviles (7, 14, 28 días)                                │
│  - Tasas por 100k habitantes                                         │
│  - Detección de incrementos súbitos                                  │
│  - Análisis de tendencias sociales                                   │
│  - Correlación oficial-social                                        │
└───────────────────────────────┬───────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         CAPA DE API                                   │
├───────────────────────────────────────────────────────────────────────┤
│  api/main.py - FastAPI Application                                   │
│                                                                       │
│  Endpoints:                                                           │
│  ┌───────────────────────────────────────────────────────────┐      │
│  │  GET  /api/v1/health          - Health check              │      │
│  │  GET  /api/v1/meta            - Metadata                  │      │
│  │  POST /api/v1/kpi             - KPIs                      │      │
│  │  GET  /api/v1/timeseries      - Serie temporal            │      │
│  │  GET  /api/v1/map/entidad     - Datos mapa                │      │
│  │  GET  /api/v1/alerts          - Alertas                   │      │
│  │  GET  /api/v1/bulletin/{id}   - Boletín                   │      │
│  │  POST /api/v1/survey          - Sondeo clínico            │      │
│  └───────────────────────────────────────────────────────────┘      │
│                                                                       │
│  Middleware:                                                          │
│  - CORS                                                               │
│  - Rate limiting (preparado)                                         │
│  - Authentication (preparado)                                        │
└───────────────────────────────┬───────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────┐
│                      CAPA DE PRESENTACIÓN                             │
├───────────────────────────────────────────────────────────────────────┤
│  dashboard/app.py - Dash Application                                 │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │                    Dashboard Web                         │        │
│  ├─────────────────────────────────────────────────────────┤        │
│  │  Header: Episcopio                                       │        │
│  ├─────────────────────────────────────────────────────────┤        │
│  │  Filtros:                                                │        │
│  │  - Entidad Federativa (dropdown)                         │        │
│  │  - Morbilidad (dropdown)                                 │        │
│  │  - Botón Actualizar                                      │        │
│  ├─────────────────────────────────────────────────────────┤        │
│  │  KPI Cards:                                              │        │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐            │        │
│  │  │  Casos    │ │  Activos  │ │Defunciones│            │        │
│  │  │  Totales  │ │           │ │           │            │        │
│  │  └───────────┘ └───────────┘ └───────────┘            │        │
│  ├─────────────────────────────────────────────────────────┤        │
│  │  Gráfico Serie Temporal                                 │        │
│  │  (Línea de casos confirmados)                           │        │
│  ├─────────────────────────────────────────────────────────┤        │
│  │  Gráfico de Sentimiento                                 │        │
│  │  (Barras de menciones + línea de sentimiento)           │        │
│  ├─────────────────────────────────────────────────────────┤        │
│  │  Alertas Activas                                        │        │
│  │  - Lista de alertas con detalles                        │        │
│  └─────────────────────────────────────────────────────────┘        │
│                                                                       │
│  Servicios:                                                           │
│  - api_client.py - Cliente HTTP para API                            │
└───────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│                       ORQUESTACIÓN                                    │
├───────────────────────────────────────────────────────────────────────┤
│  orchestrator/scheduler.py - Scheduler de Jobs                        │
│                                                                       │
│  Jobs:                                                                │
│  ┌──────────────────────────────────────────────────┐               │
│  │  Ingesta Oficial  (cada 6 horas)                 │               │
│  │  ├─ fetch_dge()                                  │               │
│  │  ├─ fetch_inegi()                                │               │
│  │  └─ normalizar_dge()                             │               │
│  └──────────────────────────────────────────────────┘               │
│                                                                       │
│  ┌──────────────────────────────────────────────────┐               │
│  │  Analítica  (cada 1 hora)                        │               │
│  │  ├─ recalcular_kpis()                            │               │
│  │  └─ evaluar_alertas()                            │               │
│  └──────────────────────────────────────────────────┘               │
└───────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│                         CONFIGURACIÓN                                 │
├───────────────────────────────────────────────────────────────────────┤
│  config/                                                              │
│  ├─ settings.yaml         - Configuración no sensible                │
│  ├─ secrets.sample.yaml   - Template de secretos                     │
│  ├─ secrets.local.yaml    - Secretos reales (no en git)              │
│  └─ loader.py             - Carga de configuración                   │
│                                                                       │
│  Prioridad:                                                           │
│  1. Variables de entorno (EP_*)                                      │
│  2. secrets.local.yaml                                               │
│  3. Valores por defecto                                              │
└───────────────────────────────────────────────────────────────────────┘
```

## Flujo de Datos

### 1. Ingesta de Datos Oficiales

```
DGE/INEGI/CONACYT
    │
    ├─> fetch_*() en ingesta/oficial.py
    │
    ├─> Descarga de CSV/JSON/API
    │
    ├─> normalizar_dge() en etl/normaliza.py
    │   ├─ Estandarizar fechas
    │   ├─ Normalizar códigos INEGI
    │   ├─ Mapear morbilidades
    │   └─ Calcular semana ISO
    │
    └─> INSERT INTO serie_oficial
```

### 2. Ingesta de Datos Sociales

```
Twitter/Facebook/Reddit
    │
    ├─> fetch_*() en ingesta/social.py
    │
    ├─> Extracción de menciones
    │
    ├─> clasificar_relevancia()
    │   └─ Filtrar por keywords
    │
    ├─> analizar_sentimiento()
    │   └─ VADER/NLTK (futuro)
    │
    └─> INSERT INTO social_menciones
```

### 3. Cálculo de KPIs y Alertas

```
Scheduler (cada hora)
    │
    ├─> recalcular_kpis()
    │   ├─ SELECT FROM serie_oficial
    │   ├─ Calcular agregados
    │   ├─ Calcular promedios móviles
    │   └─ Almacenar en cache/vista
    │
    └─> evaluar_alertas()
        ├─ Cargar reglas desde YAML
        ├─ Evaluar cada regla
        ├─ Comparar con umbrales
        └─> INSERT INTO alerta (si procede)
```

### 4. Presentación de Datos

```
Usuario → Dashboard (http://localhost:8050)
    │
    ├─> Seleccionar filtros
    │
    ├─> Botón "Actualizar" → callback Dash
    │
    ├─> api_client.get_kpis(payload)
    │   │
    │   └─> POST http://api:8000/api/v1/kpi
    │       │
    │       ├─> FastAPI procesa request
    │       ├─> Query a PostgreSQL
    │       └─> Response JSON
    │
    ├─> Renderizar gráficos con Plotly
    │   ├─ Serie temporal
    │   └─ Sentimiento
    │
    └─> Mostrar alertas activas
```

## Tecnologías por Capa

### Ingesta
- **Lenguaje**: Python 3.11+
- **Librerías**: requests, pandas
- **Futuro**: Tweepy, Facebook SDK, praw

### ETL
- **Lenguaje**: Python 3.11+
- **Librerías**: pandas, numpy
- **Futuro**: Great Expectations

### Persistencia
- **Base de datos**: PostgreSQL 16 + PostGIS 3.4
- **Cache**: Redis 7
- **Driver**: psycopg2

### Analítica
- **Lenguaje**: Python 3.11+
- **Librerías**: pandas, numpy
- **Futuro**: scikit-learn, NLTK, statsmodels

### API
- **Framework**: FastAPI 0.109.0
- **Servidor**: Uvicorn
- **Validación**: Pydantic 2.5.3

### Dashboard
- **Framework**: Dash 2.14.2
- **Visualización**: Plotly 5.18.0
- **HTTP**: requests

### Orquestación
- **Librería**: schedule 1.2.0
- **Futuro**: Apache Airflow / Prefect

### Infraestructura
- **Contenedores**: Docker
- **Orquestación**: Docker Compose
- **Futuro**: Kubernetes

## Patrones de Diseño

### 1. Separación de Capas (Layered Architecture)
- Cada capa tiene responsabilidad única
- Comunicación mediante interfaces definidas
- Permite cambiar implementación sin afectar otras capas

### 2. API Gateway Pattern
- FastAPI actúa como punto único de entrada
- Abstraer complejidad de base de datos
- Permite versionado de API

### 3. ETL Pipeline Pattern
- Flujo unidireccional de datos
- Transformaciones independientes
- Idempotencia en operaciones

### 4. Configuration Management
- Configuración externa al código
- Diferentes ambientes (dev, prod)
- Jerarquía de configuración

### 5. Health Check Pattern
- Cada servicio expone endpoint de salud
- Docker health checks
- Permite restart automático

## Escalabilidad (Futuro)

### Horizontal Scaling
```
Load Balancer
    │
    ├─> API Instance 1
    ├─> API Instance 2
    └─> API Instance N
        │
        └─> PostgreSQL (Primary-Replica)
```

### Caching Strategy
```
Request → Redis Cache
    │         │
    │         ├─ HIT → Return cached data
    │         │
    │         └─ MISS
    │              │
    │              ├─> Query PostgreSQL
    │              ├─> Store in Redis
    │              └─> Return data
```

### Message Queue (Futuro)
```
Ingesta → RabbitMQ/Kafka → Workers → Database
```

## Seguridad

### Niveles de Seguridad
1. **Network**: Docker network aislada
2. **Application**: CORS, Rate limiting
3. **Data**: Sin PII, datos agregados
4. **Secrets**: Variables de entorno, nunca en código

### Flujo de Autenticación (V1)
```
Usuario → Login
    │
    ├─> POST /auth/login
    │
    ├─> Validar credenciales
    │
    └─> JWT Token
        │
        └─> Request con Token en header
            │
            └─> Validar Token → Acceso
```

## Monitoreo y Observabilidad (V1)

```
┌─────────────────────────────────────────────┐
│               Prometheus                    │
│  (Recolección de métricas)                 │
└───────────┬─────────────────────────────────┘
            │
            ├─> API metrics (latencia, RPS)
            ├─> Database metrics (queries, connections)
            └─> System metrics (CPU, RAM)
            │
            ▼
┌─────────────────────────────────────────────┐
│               Grafana                       │
│  (Visualización de métricas)               │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│            Logs Centralizados               │
│  (ELK Stack o Loki)                        │
└─────────────────────────────────────────────┘
```

## Backup y Recuperación (V1)

```
PostgreSQL
    │
    ├─> pg_dump (diario)
    │   └─> S3/Object Storage
    │
    └─> WAL archiving (continuo)
        └─> Point-in-time recovery
```

## Referencias

- [Documento 1](episcopio_documento_1_guia_de_producto_y_construccion_alto_nivel.md): Guía de producto
- [Documento 2](episcopio_documento_2_especificacion_tecnica_y_manual_de_construccion.md): Especificación técnica
- [README.md](README.md): Documentación general
- [QUICKSTART.md](QUICKSTART.md): Inicio rápido
