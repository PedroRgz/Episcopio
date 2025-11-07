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

- Python 3.11+
- Git
- PostgreSQL 16+ (local o Azure)
- Redis (opcional, para caché)

### Instalación Local

1. **Clonar el repositorio**

```bash
git clone https://github.com/PedroRgz/Episcopio.git
cd Episcopio
```

2. **Ejecutar script de inicio automático**

```bash
./run_local.sh
```

Esto creará un entorno virtual, instalará dependencias y arrancará ambos servicios (API y Dashboard).

3. **Acceder a la aplicación**

- **Dashboard**: http://localhost:8050
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Despliegue en Azure

Para desplegar en producción usando Azure Web Apps o una VM de Azure, consulta la [Guía de Despliegue en Azure](AZURE_DEPLOYMENT.md) que incluye:

- Configuración de Azure Web Apps
- Configuración de VM en Azure
- Configuración de PostgreSQL y Redis
- Variables de entorno requeridas (ver abajo)
- SSL/HTTPS
- Monitoreo y backup

#### Variables de Entorno para Azure

Las siguientes variables de entorno deben configurarse al desplegar en Azure:

**Requeridas:**
- `EP_POSTGRES_HOST` - Host del servidor PostgreSQL
- `EP_POSTGRES_USER` - Usuario de PostgreSQL
- `EP_POSTGRES_PASSWORD` - Contraseña de PostgreSQL
- `EP_POSTGRES_DATABASE` - Nombre de la base de datos
- `EP_SECURITY_CORS_ALLOWED_ORIGINS` - Orígenes permitidos para CORS (separados por comas), ej: `https://episcopio.mx,https://www.episcopio.mx`

**Opcionales:**
- `EP_API_URL` - URL base para el API. Configuración según escenario: `http://localhost:8000` para Azure Web Apps (servicios en mismo contenedor, configurado por startup.sh), `/api` para reverse proxy (nginx/Azure Application Gateway), o URL completa para servicios en hosts separados.
- `EP_REDIS_URL` - URL de Redis para caché
- `EP_POSTGRES_PORT` - Puerto de PostgreSQL (default: 5432)

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

### Desarrollo Local Simplificado

Para desarrollo local, simplemente ejecuta:

```bash
./run_local.sh
```

Este script automáticamente:
- Crea y activa un entorno virtual
- Instala todas las dependencias
- Configura variables de entorno
- Inicia API y Dashboard

### Jupyter Notebook - Exploración de ETL

Para explorar y ejecutar procesos ETL paso a paso:

```bash
# Instalar Jupyter (si no está instalado)
pip install jupyter

# Ejecutar notebook
jupyter notebook episcopio_etl_notebook.ipynb
```

El notebook incluye:
- Ingesta de datos oficiales y sociales
- Normalización y transformación
- Cálculo de KPIs
- Generación de alertas
- Visualizaciones interactivas

### Ejecutar servicios individualmente

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

## ☁️ Despliegue en Producción

### Azure Web Apps (Recomendado)

La forma más sencilla de desplegar Episcopio en producción es usando Azure Web Apps:

```bash
# Crear recursos en Azure
az webapp up --name episcopio-app --runtime "PYTHON:3.11"
```

### Azure VM

Para mayor control, puedes desplegar en una máquina virtual:

```bash
# Crear VM
az vm create --name episcopio-vm --image Ubuntu2204

# SSH y configurar
ssh azureuser@<IP>
git clone https://github.com/PedroRgz/Episcopio.git
cd Episcopio
./run_local.sh
```

Ver [AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md) para instrucciones detalladas.

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