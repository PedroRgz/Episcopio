# Episcopio

**Tomando el pulso epidemiológico de México**

Episcopio es una plataforma de monitoreo epidemiológico que integra datos oficiales (DGE/SINAVE, INEGI, CONACYT) con señales complementarias (sondeos clínicos y monitoreo de redes sociales) para ofrecer visualizaciones prácticas, alertas tempranas y boletines ejecutivos destinados a profesionales de la salud.

## 🎯 Características del MVP

- **Panel oficial**: KPIs (casos confirmados, activos, defunciones), series temporales y mapas por entidad
- **Panel social**: Análisis de menciones en redes sociales con análisis de sentimiento básico
- **Alertas**: Reglas simples para detectar incrementos súbitos y cambios de tendencia
- **Dashboard interactivo**: Visualización en tiempo real con Dash/Plotly
- **API REST**: Endpoints para consulta de datos epidemiológicos
- **Arquitectura modular**: Fácil de extender y mantener

## 🏗️ Arquitectura

```
episcopio/
├── api/                      # FastAPI: endpoints de lectura
├── analytics/                # KPIs, sentimiento, correlación, alertas
├── dashboard/                # Dash/Plotly dashboard web
├── db/                       # Schema, migraciones, seeds
├── etl/                      # Transformaciones y normalizadores
├── ingesta/                  # Conectores a fuentes oficiales/sociales
├── orchestrator/             # Scheduler para jobs automáticos
├── config/                   # Configuración y secretos
└── infra/                    # Docker Compose, IaC
```

## 🚀 Inicio Rápido

### Prerrequisitos

- Docker y Docker Compose
- Python 3.11+ (para desarrollo local)
- Git

### Instalación

1. **Clonar el repositorio**

```bash
git clone https://github.com/PedroRgz/Episcopio.git
cd Episcopio
```

2. **Configurar variables de entorno**

```bash
cd infra
cp .env.example .env
# Edita .env con tus credenciales
```

3. **Configurar secretos (opcional)**

```bash
cd ../config
cp secrets.sample.yaml secrets.local.yaml
# Edita secrets.local.yaml con tus API keys
```

4. **Iniciar la aplicación**

```bash
cd ../infra
docker-compose up -d --build
```

5. **Inicializar la base de datos**

```bash
# Ejecutar el schema SQL
docker exec -i episcopio-db psql -U episcopio -d episcopio < ../db/schema/schema.sql

# Cargar datos semilla
docker exec -i episcopio-db psql -U episcopio -d episcopio < ../db/seeds/seed_entidades.sql
docker exec -i episcopio-db psql -U episcopio -d episcopio < ../db/seeds/seed_morbilidades.sql
```

6. **Acceder a la aplicación**

- **Dashboard**: http://localhost:8050
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📊 Uso

### Dashboard

Accede al dashboard en http://localhost:8050 para:

- Visualizar KPIs por entidad federativa
- Ver series temporales de casos y defunciones
- Analizar sentimiento en redes sociales
- Revisar alertas activas
- Filtrar por entidad y morbilidad

### API

La API REST está disponible en http://localhost:8000/api/v1/

Endpoints principales:

- `GET /api/v1/health` - Verificar estado del servicio
- `GET /api/v1/meta` - Metadatos de fuentes
- `POST /api/v1/kpi` - Obtener KPIs
- `GET /api/v1/timeseries` - Serie temporal
- `GET /api/v1/map/entidad` - Datos para mapa
- `GET /api/v1/alerts` - Alertas activas
- `POST /api/v1/survey` - Enviar sondeo clínico

Documentación interactiva disponible en http://localhost:8000/docs

## 🛠️ Desarrollo

### Desarrollo Local

1. **Crear entorno virtual**

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

2. **Instalar dependencias**

```bash
pip install -r api/requirements.txt
pip install -r dashboard/requirements.txt
pip install -r orchestrator/requirements.txt
```

3. **Configurar variables de entorno**

```bash
export EP_POSTGRES_HOST=localhost
export EP_POSTGRES_USER=episcopio
export EP_POSTGRES_PASSWORD=changeme
export EP_POSTGRES_DATABASE=episcopio
```

4. **Ejecutar servicios individualmente**

```bash
# API
cd api
python main.py

# Dashboard
cd dashboard
python app.py

# Scheduler
cd orchestrator
python scheduler.py
```

### Ejecutar Tests

```bash
# Linting
flake8 api/ dashboard/ analytics/ etl/ ingesta/

# Validar configuración
python -c "import yaml; yaml.safe_load(open('config/settings.yaml'))"
python -c "import yaml; yaml.safe_load(open('config/secrets.sample.yaml'))"
```

## 📁 Estructura de Datos

### Base de Datos PostgreSQL + PostGIS

Tablas principales:

- `geo_entidad` - Catálogo de entidades federativas
- `geo_municipio` - Catálogo de municipios
- `morbilidad` - Catálogo de enfermedades
- `serie_oficial` - Datos epidemiológicos oficiales
- `social_menciones` - Menciones en redes sociales
- `sondeo_clinico` - Sondeos clínicos anónimos
- `alerta` - Alertas generadas
- `boletin` - Boletines epidemiológicos

Ver schema completo en `db/schema/schema.sql`

## 🔧 Configuración

### Configuración Estática

Editar `config/settings.yaml`:

```yaml
app:
  timezone: "America/Merida"
  
alerts:
  alert_windows_days: 14
  delta_threshold: 0.2
  
analytics:
  moving_window_days: [7, 14, 28]
```

### Secretos

Las credenciales se gestionan mediante:

1. **Archivo YAML** (desarrollo): `config/secrets.local.yaml`
2. **Variables de entorno** (producción): Prefijo `EP_`

Las variables de entorno tienen prioridad sobre el archivo YAML.

### Reglas de Alertas

Editar `analytics/reglas/alertas.yaml` para configurar reglas personalizadas.

## 🐳 Docker

### Construir imágenes

```bash
# Construir todas las imágenes
docker-compose -f infra/docker-compose.yml build

# Construir imagen específica
docker-compose -f infra/docker-compose.yml build api
```

### Ver logs

```bash
# Todos los servicios
docker-compose -f infra/docker-compose.yml logs -f

# Servicio específico
docker-compose -f infra/docker-compose.yml logs -f api
```

### Detener servicios

```bash
docker-compose -f infra/docker-compose.yml down

# Eliminar volúmenes también
docker-compose -f infra/docker-compose.yml down -v
```

## 📖 Documentación

- **Documento 1**: [Guía de Producto y Construcción](episcopio_documento_1_guia_de_producto_y_construccion_alto_nivel.md)
- **Documento 2**: [Especificación Técnica](episcopio_documento_2_especificacion_tecnica_y_manual_de_construccion.md)

## 🔒 Seguridad y Privacidad

- **Anonimato absoluto** en sondeos clínicos (sin PII)
- **Principio de mínima retención**: solo agregados geotemporales
- **Rate limiting** en API para prevenir abuso
- **CORS configurado** para orígenes permitidos
- **Secretos nunca en código**: usar variables de entorno o vault

## 🗺️ Roadmap

### MVP (Actual)
- ✅ Conectores básicos DGE/INEGI
- ✅ API de lectura con FastAPI
- ✅ Dashboard con Dash/Plotly
- ✅ Reglas de alertas simples
- ✅ Schema de base de datos
- ✅ Docker Compose para despliegue

### V1 (Próximamente)
- [ ] Filtros avanzados (municipio, edad, sexo)
- [ ] Detección de anomalías (z-score, STL, CUSUM)
- [ ] Perfiles de usuario/roles
- [ ] Panel de calidad de datos
- [ ] API pública con rate limiting
- [ ] Exportación PDF/HTML
- [ ] Webhooks de alertas

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo licencia MIT. Ver archivo `LICENSE` para más detalles.

## 👥 Autores

- **Pedro Rodríguez** - Creador y mantenedor principal

## 🙏 Agradecimientos

- DGE/SINAVE por datos epidemiológicos oficiales
- INEGI por datos demográficos y socioeconómicos
- CONACYT por datos de COVID-19
- Comunidad open source por las herramientas utilizadas

---

**Contacto**: Para preguntas o soporte, abre un issue en GitHub.

**Nota**: Este es un MVP. Los datos mostrados son de ejemplo. Para producción, configurar conectores reales a fuentes de datos.