# Guía de Pruebas - Episcopio MVP

Esta guía documenta cómo probar cada componente del sistema Episcopio.

## Pruebas sin Docker (Módulos Python)

### 1. Configuración

```bash
# Instalar dependencias
pip install -r requirements.txt

# Probar carga de configuración
python config/loader.py
```

**Resultado esperado:**
```
App: Episcopio v1.0.0-mvp
Timezone: America/Merida
Database: episcopio
```

### 2. ETL y Normalización

```bash
python etl/normaliza.py
```

**Resultado esperado:**
- Normalización de fechas (DD/MM/YYYY → YYYY-MM-DD)
- Normalización de códigos de entidad (padding con ceros)
- Mapeo de morbilidades a catálogo estándar
- Cálculo de semanas ISO

### 3. Ingesta de Datos

```bash
# Conectores oficiales
python ingesta/oficial.py

# Conectores sociales
python ingesta/social.py
```

**Resultado esperado:**
- Simulación de conexión a fuentes oficiales (DGE, INEGI, CONACYT)
- Simulación de conexión a redes sociales (Twitter, Facebook, Reddit)
- Clasificación de relevancia de texto

### 4. Analytics

```bash
# Cálculo de KPIs
python analytics/kpis.py

# Evaluación de alertas
python analytics/alertas.py
```

**Resultado esperado:**
- Cálculo mock de KPIs
- Evaluación de reglas de alertas
- Carga de reglas desde YAML

### 5. Validación de Configuración

```bash
make test
```

**Resultado esperado:**
```
Running configuration validation...
✓ Configuration files are valid
```

## Pruebas con Docker

### 1. Build de Imágenes

```bash
# Build todas las imágenes
make build

# O individualmente
docker build -f api/Dockerfile -t episcopio-api .
docker build -f dashboard/Dockerfile -t episcopio-dashboard .
docker build -f orchestrator/Dockerfile -t episcopio-scheduler .
```

### 2. Inicio de Servicios

```bash
# Iniciar todos los servicios
make up

# Verificar estado
make status
```

**Resultado esperado:**
```
NAME                    STATUS   PORTS
episcopio-db            Up       0.0.0.0:5432->5432/tcp
episcopio-redis         Up       0.0.0.0:6379->6379/tcp
episcopio-api           Up       0.0.0.0:8000->8000/tcp
episcopio-dashboard     Up       0.0.0.0:8050->8050/tcp
episcopio-scheduler     Up
```

### 3. Pruebas de Health Check

```bash
# API Health Check
curl http://localhost:8000/api/v1/health

# Resultado esperado:
# {"ok":true,"service":"episcopio-api","version":"1.0.0-mvp"}

# Root endpoint
curl http://localhost:8000/

# Resultado esperado:
# {"app":"Episcopio","version":"1.0.0-mvp","status":"operational","docs":"/docs"}
```

### 4. Pruebas de Base de Datos

```bash
# Conectar a PostgreSQL
make shell-db

# Dentro del shell:
# Verificar tablas
\dt

# Verificar entidades
SELECT COUNT(*) FROM geo_entidad;

# Verificar morbilidades
SELECT * FROM morbilidad;
```

**Resultado esperado:**
- 32 entidades federativas
- 15 morbilidades precargadas

### 5. Pruebas de API Endpoints

```bash
# Metadata
curl http://localhost:8000/api/v1/meta

# KPIs
curl -X POST http://localhost:8000/api/v1/kpi \
  -H "Content-Type: application/json" \
  -d '{"entidad": "31"}'

# Timeseries
curl "http://localhost:8000/api/v1/timeseries?entidad=31"

# Map data
curl http://localhost:8000/api/v1/map/entidad

# Alerts
curl "http://localhost:8000/api/v1/alerts?estado=activa"
```

### 6. Pruebas de Dashboard

```bash
# Abrir en navegador
open http://localhost:8050

# O con curl para verificar que responde
curl -I http://localhost:8050
```

**Checklist del Dashboard:**
- [ ] Página carga sin errores
- [ ] KPIs se muestran (Casos Totales, Casos Activos, Defunciones)
- [ ] Dropdown de entidades funciona
- [ ] Dropdown de morbilidades funciona
- [ ] Botón "Actualizar" funciona
- [ ] Gráfico de serie temporal se renderiza
- [ ] Gráfico de sentimiento se renderiza
- [ ] Sección de alertas muestra información

### 7. Pruebas de Scheduler

```bash
# Ver logs del scheduler
make logs-scheduler

# Resultado esperado:
# Líneas indicando:
# - Iniciando job de ingesta oficial
# - Conectando a DGE...
# - Conectando a INEGI...
# - Iniciando job de analítica
# - Recalculando KPIs...
# - Evaluando alertas...
```

### 8. Pruebas de Integración

```bash
# Verificar comunicación API → Database
docker exec episcopio-api python -c "
import psycopg2
conn = psycopg2.connect(
    host='db',
    user='episcopio',
    password='changeme',
    database='episcopio'
)
print('✓ Conexión a base de datos exitosa')
conn.close()
"

# Verificar comunicación Dashboard → API
docker exec episcopio-dashboard python -c "
from services.api_client import api_client
result = api_client.health()
print(f'✓ Dashboard puede comunicarse con API: {result}')
"
```

## Pruebas de Estrés

### 1. API Load Test (con Apache Bench)

```bash
# 100 requests, 10 concurrent
ab -n 100 -c 10 http://localhost:8000/api/v1/health

# 1000 requests, 50 concurrent al endpoint de KPIs
ab -n 1000 -c 50 -p kpi_payload.json -T application/json http://localhost:8000/api/v1/kpi
```

### 2. Monitoreo de Recursos

```bash
# Ver uso de recursos de cada contenedor
docker stats
```

## Pruebas de Seguridad Básicas

### 1. CORS

```bash
# Intentar acceso desde origen no permitido
curl -H "Origin: http://malicious-site.com" \
  -H "Access-Control-Request-Method: POST" \
  -X OPTIONS http://localhost:8000/api/v1/kpi
```

### 2. SQL Injection (debe fallar)

```bash
# Intentar inyección SQL en parámetro
curl "http://localhost:8000/api/v1/timeseries?entidad=31'; DROP TABLE geo_entidad; --"
```

### 3. Rate Limiting

```bash
# Hacer muchas requests rápidas para verificar rate limiting
for i in {1..100}; do
  curl http://localhost:8000/api/v1/health
done
```

## Limpieza Después de Pruebas

```bash
# Detener servicios
make down

# Eliminar todo (incluyendo volúmenes)
make clean
```

## Solución de Problemas de Pruebas

### Error: "Cannot connect to API"

```bash
# Verificar que el contenedor está corriendo
docker ps | grep episcopio-api

# Ver logs de errores
docker logs episcopio-api

# Reiniciar API
docker-compose -f infra/docker-compose.yml restart api
```

### Error: "Database connection refused"

```bash
# Verificar que PostgreSQL está listo
docker exec episcopio-db pg_isready -U episcopio

# Verificar que las tablas existen
make shell-db
\dt
```

### Dashboard no carga datos

```bash
# Verificar logs del dashboard
make logs-dashboard

# Verificar que la API está accesible desde el dashboard
docker exec episcopio-dashboard curl http://api:8000/api/v1/health
```

## Checklist Completo de Pruebas MVP

- [ ] Configuración carga correctamente
- [ ] ETL normaliza datos correctamente
- [ ] Conectores se ejecutan sin errores
- [ ] Analytics calcula KPIs (mock)
- [ ] Alertas se evalúan correctamente
- [ ] Docker Compose levanta todos los servicios
- [ ] Base de datos se inicializa con schema
- [ ] Datos semilla se cargan correctamente
- [ ] API responde a health check
- [ ] API responde a todos los endpoints
- [ ] Dashboard carga en el navegador
- [ ] Dashboard muestra KPIs
- [ ] Dashboard muestra gráficos
- [ ] Dashboard muestra alertas
- [ ] Scheduler ejecuta jobs periódicos
- [ ] Logs se generan correctamente
- [ ] Servicios se reinician automáticamente
- [ ] Comunicación entre servicios funciona

## Próximos Pasos de Testing (V1)

- Pruebas unitarias con pytest
- Pruebas de integración automatizadas
- Pruebas end-to-end con Selenium
- Pruebas de rendimiento con Locust
- Pruebas de seguridad con OWASP ZAP
- Cobertura de código con coverage.py
