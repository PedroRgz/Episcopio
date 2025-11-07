# Guía de Despliegue en Azure

Esta guía describe cómo desplegar Episcopio en Azure usando Azure Web Apps o una máquina virtual.

## Arquitectura de Despliegue

Episcopio utiliza una **arquitectura unificada** donde ambos servicios (API y Dashboard) corren en un solo proceso:

- **Proceso unificado**: API (FastAPI) + Dashboard (Dash/Plotly) en un solo proceso Python
- **Puerto único**: Todo el tráfico en puerto 8000
- **Dashboard**: Accesible en la ruta raíz `/`
- **API REST**: Disponible en `/api/v1/*`
- **Comunicación**: El Dashboard usa rutas relativas (`/api/v1`) para llamar a la API

### Ventajas de la Arquitectura Unificada

- ✅ **Simplicidad**: Un solo proceso, un solo puerto, menor complejidad operacional
- ✅ **Menor latencia**: Sin overhead de red entre API y Dashboard (mismo proceso)
- ✅ **Menos recursos**: Menor consumo de memoria y CPU
- ✅ **Despliegue simple**: No requiere configurar múltiples servicios o ports
- ✅ **Health checks simples**: Azure solo necesita monitorear un endpoint
- ✅ **Ideal para Azure App Service**: Alineado con el modelo de un solo puerto de Azure

### Diagrama de Arquitectura

```
┌─────────────────────────────────────┐
│   Azure App Service / VM            │
│   ┌─────────────────────────────┐   │
│   │  Unified Process (Port 8000)│   │
│   │  ┌──────────────────────┐   │   │
│   │  │  FastAPI             │   │   │
│   │  │  - Routes /api/v1/*  │   │   │
│   │  └──────────────────────┘   │   │
│   │  ┌──────────────────────┐   │   │
│   │  │  Dash (mounted at /) │   │   │
│   │  │  - Dashboard UI      │   │   │
│   │  └──────────────────────┘   │   │
│   └─────────────────────────────┘   │
└─────────────────────────────────────┘
         ↓
    Users access via:
    - Dashboard: https://app.com/
    - API: https://app.com/api/v1/*
```

### Estrategias de Despliegue Alternativas (Legacy)

**Nota**: Estas opciones están disponibles para casos especiales, pero se recomienda la arquitectura unificada.

**Opción B: Azure VM con reverse proxy**
- Servicios detrás de Nginx que actúa como reverse proxy
- Requiere configuración adicional de nginx
- Solo usar si necesitas routing avanzado o servicios separados

**Opción C: Servicios en dominios separados**
- API en `https://api.episcopio.mx`, Dashboard en `https://episcopio.mx`
- Mayor costo y complejidad
- Solo usar si necesitas escalabilidad independiente de servicios

## Opción A: Azure Web Apps (Recomendado)

Azure Web Apps es la forma más sencilla de desplegar aplicaciones Python en Azure sin preocuparse por la infraestructura. La arquitectura unificada de Episcopio es ideal para Azure Web Apps.

### Prerrequisitos

- Cuenta de Azure activa
- Azure CLI instalado (`az cli`)
- Git configurado

### Paso 1: Preparar la aplicación

La aplicación ya está configurada para Azure Web Apps. Los archivos importantes son:

- `startup.sh` - Script de inicio para Azure
- `requirements.txt` - Dependencias de Python
- `azure-webapp.json` - Configuración de Azure Web App

### Paso 2: Crear recursos en Azure

```bash
# Iniciar sesión en Azure
az login

# Crear un grupo de recursos
az group create --name episcopio-rg --location eastus

# Crear un plan de App Service
az appservice plan create \
  --name episcopio-plan \
  --resource-group episcopio-rg \
  --sku B1 \
  --is-linux

# Crear la Web App
az webapp create \
  --name episcopio-app \
  --resource-group episcopio-rg \
  --plan episcopio-plan \
  --runtime "PYTHON:3.11"
```

### Paso 3: Configurar PostgreSQL en Azure

```bash
# Crear servidor PostgreSQL
az postgres flexible-server create \
  --name episcopio-db \
  --resource-group episcopio-rg \
  --location eastus \
  --admin-user episcopio \
  --admin-password <CONTRASEÑA_SEGURA> \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 16

# Crear base de datos
az postgres flexible-server db create \
  --resource-group episcopio-rg \
  --server-name episcopio-db \
  --database-name episcopio

# Habilitar acceso desde Azure services
az postgres flexible-server firewall-rule create \
  --resource-group episcopio-rg \
  --name episcopio-db \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

### Paso 4: Configurar Redis en Azure (Opcional)

```bash
# Crear Redis Cache
az redis create \
  --name episcopio-redis \
  --resource-group episcopio-rg \
  --location eastus \
  --sku Basic \
  --vm-size c0
```

### Paso 5: Configurar variables de entorno

```bash
# Obtener el dominio de tu aplicación
APP_DOMAIN="episcopio-app.azurewebsites.net"

# Configurar variables de entorno en la Web App
az webapp config appsettings set \
  --name episcopio-app \
  --resource-group episcopio-rg \
  --settings \
    EP_POSTGRES_HOST=episcopio-db.postgres.database.azure.com \
    EP_POSTGRES_USER=episcopio \
    EP_POSTGRES_PASSWORD=<CONTRASEÑA_SEGURA> \
    EP_POSTGRES_DATABASE=episcopio \
    EP_POSTGRES_PORT=5432 \
    EP_API_URL=/api/v1 \
    EP_SECURITY_CORS_ALLOWED_ORIGINS="https://${APP_DOMAIN},https://www.${APP_DOMAIN}"
```

**Notas importantes sobre variables de entorno:**

- `EP_API_URL`: Para la arquitectura unificada, use `/api/v1` (ruta relativa). El Dashboard y la API están en el mismo proceso y usan rutas relativas para comunicarse.
- `EP_SECURITY_CORS_ALLOWED_ORIGINS`: Lista separada por comas de orígenes permitidos. Incluya todos los dominios desde donde se accederá a la aplicación (con y sin www si aplica).
- **WEBSITES_PORT ya no es necesario**: Azure detecta automáticamente el puerto 8000 del proceso unificado.

Si usa un dominio personalizado (ej: `episcopio.mx`), actualice la variable CORS:
```bash
az webapp config appsettings set \
  --name episcopio-app \
  --resource-group episcopio-rg \
  --settings \
    EP_SECURITY_CORS_ALLOWED_ORIGINS="https://episcopio.mx,https://www.episcopio.mx"
```

### Paso 6: Desplegar la aplicación

```bash
# Configurar despliegue desde repositorio Git
az webapp deployment source config \
  --name episcopio-app \
  --resource-group episcopio-rg \
  --repo-url https://github.com/PedroRgz/Episcopio.git \
  --branch main \
  --manual-integration

# O desplegar desde código local
cd /ruta/a/Episcopio
az webapp up \
  --name episcopio-app \
  --resource-group episcopio-rg \
  --runtime "PYTHON:3.11"
```

### Paso 7: Inicializar la base de datos

```bash
# Conectarse al servidor PostgreSQL
psql "host=episcopio-db.postgres.database.azure.com port=5432 dbname=episcopio user=episcopio password=<CONTRASEÑA> sslmode=require"

# Ejecutar scripts de inicialización
\i db/schema/schema.sql
\i db/seeds/seed_entidades.sql
\i db/seeds/seed_morbilidades.sql
\q
```

### Paso 8: Verificar el despliegue

```bash
# Abrir la aplicación en el navegador
az webapp browse --name episcopio-app --resource-group episcopio-rg

# Ver logs en tiempo real
az webapp log tail --name episcopio-app --resource-group episcopio-rg
```

La aplicación estará disponible en: `https://episcopio-app.azurewebsites.net`

- **Dashboard**: `https://episcopio-app.azurewebsites.net/`
- **API Health**: `https://episcopio-app.azurewebsites.net/api/v1/health`
- **API Docs**: `https://episcopio-app.azurewebsites.net/docs`

---

## Opción B: Máquina Virtual en Azure (Despliegue Directo)

**Nota**: Con la arquitectura unificada, ya no necesitas Nginx para enrutar entre servicios. Simplemente despliega el proceso unificado en la VM.

### Paso 1: Crear una VM

```bash
# Crear VM Ubuntu
az vm create \
  --name episcopio-vm \
  --resource-group episcopio-rg \
  --image Ubuntu2204 \
  --size Standard_B2s \
  --admin-username azureuser \
  --generate-ssh-keys

# Abrir puerto para HTTP (o 443 para HTTPS con certbot)
az vm open-port --port 80 --resource-group episcopio-rg --name episcopio-vm
az vm open-port --port 443 --resource-group episcopio-rg --name episcopio-vm --priority 1001
```

### Paso 2: Conectarse a la VM

```bash
# Obtener la IP pública
IP=$(az vm show -d --resource-group episcopio-rg --name episcopio-vm --query publicIps -o tsv)

# Conectarse por SSH
ssh azureuser@$IP
```

### Paso 3: Instalar dependencias en la VM

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# Instalar PostgreSQL
sudo apt install -y postgresql postgresql-contrib postgis

# Instalar Redis
sudo apt install -y redis-server

# Instalar Nginx (para proxy reverso)
sudo apt install -y nginx
```

### Paso 4: Clonar y configurar la aplicación

```bash
# Clonar repositorio
git clone https://github.com/PedroRgz/Episcopio.git
cd Episcopio

# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 5: Configurar PostgreSQL

```bash
# Configurar PostgreSQL
sudo -u postgres psql

CREATE DATABASE episcopio;
CREATE USER episcopio WITH PASSWORD 'changeme';
GRANT ALL PRIVILEGES ON DATABASE episcopio TO episcopio;
CREATE EXTENSION postgis;
\q

# Inicializar base de datos
psql -U episcopio -d episcopio < db/schema/schema.sql
psql -U episcopio -d episcopio < db/seeds/seed_entidades.sql
psql -U episcopio -d episcopio < db/seeds/seed_morbilidades.sql
```

### Paso 6: Configurar variables de entorno

```bash
# Obtener la IP pública o dominio de la VM
PUBLIC_DOMAIN="<your-domain.com>"  # o usar IP pública

# Crear archivo .env
cat > .env << EOF
EP_POSTGRES_HOST=localhost
EP_POSTGRES_USER=episcopio
EP_POSTGRES_PASSWORD=changeme
EP_POSTGRES_DATABASE=episcopio
EP_POSTGRES_PORT=5432
EP_REDIS_URL=redis://localhost:6379/0
EP_API_URL=/api/v1
EP_SECURITY_CORS_ALLOWED_ORIGINS=https://${PUBLIC_DOMAIN},http://${PUBLIC_DOMAIN}
EOF

# Cargar variables de entorno
export $(cat .env | xargs)
```

**Nota:** Con la arquitectura unificada, use `EP_API_URL=/api/v1` para comunicación interna en el mismo proceso.

### Paso 7: Configurar servicio systemd

```bash
# Crear servicio para la aplicación unificada
sudo tee /etc/systemd/system/episcopio.service > /dev/null << EOF
[Unit]
Description=Episcopio Unified Application (API + Dashboard)
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=azureuser
WorkingDirectory=/home/azureuser/Episcopio
Environment="PATH=/home/azureuser/Episcopio/venv/bin"
EnvironmentFile=/home/azureuser/Episcopio/.env
ExecStart=/home/azureuser/Episcopio/venv/bin/gunicorn api.unified:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile /var/log/episcopio-access.log \
  --error-logfile /var/log/episcopio-error.log \
  --log-level info
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Habilitar e iniciar servicio
sudo systemctl daemon-reload
sudo systemctl enable episcopio
sudo systemctl start episcopio
```

### Paso 8: (Opcional) Configurar Nginx como proxy reverso para HTTPS

Si quieres usar HTTPS con Let's Encrypt, puedes configurar Nginx como proxy reverso:

```bash
# Instalar Nginx
sudo apt install -y nginx

# Configurar Nginx para proxy pass al puerto 8000
sudo tee /etc/nginx/sites-available/episcopio > /dev/null << EOF
server {
    listen 80;
    server_name _;

    # Proxy pass todo el tráfico al proceso unificado en puerto 8000
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/episcopio /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

**Cómo funciona:**
1. Usuario accede a `http://your-domain.com` → Nginx enruta a Dashboard (puerto 8050)
2. Dashboard hace peticiones a `/api/*` → Nginx enruta a API (puerto 8000)
3. Solo se expone el puerto 80/443 externamente; los puertos 8000 y 8050 permanecen internos

### Paso 9: Verificar el despliegue

```bash
# Verificar servicios
sudo systemctl status episcopio-api
sudo systemctl status episcopio-dashboard

# Ver logs
sudo systemctl restart nginx
```

### Paso 9: Verificar el despliegue

```bash
# Verificar servicio
sudo systemctl status episcopio

# Ver logs
sudo journalctl -u episcopio -f
```

La aplicación estará disponible en: `http://<IP_PUBLICA_VM>:8000`

Si configuraste Nginx, accede vía: `http://<IP_PUBLICA_VM>`

- **Dashboard**: `http://<IP>/`
- **API Health**: `http://<IP>/api/v1/health`
- **API Docs**: `http://<IP>/docs`

---

## Configuración SSL/HTTPS (Opcional pero recomendado)

### Para Azure Web Apps

Azure Web Apps incluye certificado SSL gratuito para dominios `*.azurewebsites.net`.

Para dominio personalizado:

```bash
# Agregar dominio personalizado
az webapp config hostname add \
  --webapp-name episcopio-app \
  --resource-group episcopio-rg \
  --hostname www.tudominio.com

# Crear certificado SSL gratuito
az webapp config ssl create \
  --resource-group episcopio-rg \
  --name episcopio-app \
  --hostname www.tudominio.com
```

### Para VM

```bash
# Instalar Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtener certificado SSL gratuito con Let's Encrypt
sudo certbot --nginx -d tudominio.com -d www.tudominio.com

# Configurar renovación automática
sudo systemctl enable certbot.timer
```

---

## Monitoreo y Logs

### Azure Web Apps

```bash
# Habilitar logs de aplicación
az webapp log config \
  --name episcopio-app \
  --resource-group episcopio-rg \
  --application-logging filesystem \
  --level information

# Ver logs en tiempo real
az webapp log tail \
  --name episcopio-app \
  --resource-group episcopio-rg
```

### VM

```bash
# Ver logs del servicio unificado
sudo journalctl -u episcopio -f

# Ver logs de aplicación
sudo tail -f /var/log/episcopio-access.log
sudo tail -f /var/log/episcopio-error.log

# Ver logs de Nginx (si configurado)
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## Escalabilidad

### Azure Web Apps

```bash
# Escalar verticalmente (aumentar recursos)
az appservice plan update \
  --name episcopio-plan \
  --resource-group episcopio-rg \
  --sku P1V2

# Escalar horizontalmente (múltiples instancias)
az appservice plan update \
  --name episcopio-plan \
  --resource-group episcopio-rg \
  --number-of-workers 3
```

### VM

- Usar Azure Load Balancer para distribuir tráfico entre múltiples VMs
- Implementar Azure Virtual Machine Scale Sets para auto-scaling

---

## Backup y Recuperación

### Base de datos PostgreSQL

```bash
# Configurar backup automático
az postgres flexible-server parameter set \
  --resource-group episcopio-rg \
  --server-name episcopio-db \
  --name backup_retention_days \
  --value 7

# Crear backup manual
az postgres flexible-server backup create \
  --resource-group episcopio-rg \
  --name episcopio-db \
  --backup-name manual-backup-$(date +%Y%m%d)
```

---

## Costos Estimados (USD/mes)

### Azure Web Apps
- App Service Plan B1: ~$13/mes
- PostgreSQL Flexible Server (Basic): ~$15/mes
- Redis Cache (Basic C0): ~$16/mes
- **Total: ~$44/mes**

### VM
- VM Standard_B2s: ~$30/mes
- Disco administrado (32GB): ~$2/mes
- IP pública: ~$3/mes
- **Total: ~$35/mes**

---

## Soporte

Para problemas o preguntas:
- Abre un issue en GitHub
- Consulta la documentación de Azure: https://docs.microsoft.com/azure

