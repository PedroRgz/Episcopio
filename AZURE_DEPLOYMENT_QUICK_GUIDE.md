# Guía Rápida de Deployment en Azure

## Configuración Requerida en Azure Portal

### Variables de Entorno (Environment Variables)

Ve a: **Settings → Environment variables → App settings**

Agrega las siguientes variables:

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `WEBSITES_PORT` | `8050` | Puerto del Dashboard (único puerto expuesto externamente) |
| `EP_POSTGRES_HOST` | `<tu-servidor>.postgres.database.azure.com` | Host de PostgreSQL |
| `EP_POSTGRES_USER` | `episcopio` | Usuario de PostgreSQL |
| `EP_POSTGRES_PASSWORD` | `<tu-contraseña>` | Contraseña de PostgreSQL |
| `EP_POSTGRES_DATABASE` | `episcopio` | Nombre de la base de datos |
| `EP_POSTGRES_PORT` | `5432` | Puerto de PostgreSQL |
| `EP_API_URL` | `http://localhost:8000` | URL interna de la API (comunicación localhost entre servicios) |
| `EP_API_WAIT_SECONDS` | `30` | Tiempo de espera para que la API inicie |

**Nota importante:** En Azure Web Apps, ambos servicios (API y Dashboard) corren en el mismo contenedor. La API (puerto 8000) solo es accesible internamente via localhost, NO está expuesta externamente. Solo el Dashboard (puerto 8050) es accesible desde Internet.

### Startup Command

Ve a: **Settings → Configuration → General settings**

**Startup Command:** `startup.sh`

### Stack Settings

- **Stack:** Python
- **Version:** Python 3.11

## Verificación Post-Deployment

1. Ve a **Monitoring → Log stream**
2. Busca estos mensajes:
   - `✓ API is ready and responding!`
   - `✓ Dashboard is running`
   - `Application started successfully!`

3. Si hay errores:
   - Revisa los logs en `/tmp/api.log` y `/tmp/dashboard.log`
   - Verifica que todas las variables de entorno estén configuradas
   - Asegúrate que la base de datos PostgreSQL sea accesible desde Azure

## Troubleshooting Común

### Error: "Container didn't respond to HTTP pings on port: 8000"

**Causa:** Azure está intentando hacer health check en el puerto 8000 (API) en lugar del 8050 (Dashboard)

**Solución:** 
- Verifica que `WEBSITES_PORT=8050` esté configurado
- Reinicia el App Service

### Error: "Syntax error: Unterminated quoted string"

**Causa:** El archivo `startup.sh` tiene caracteres incorrectos o line endings de Windows

**Solución:**
- Asegúrate de que el archivo tenga line endings LF (no CRLF)
- Verifica que no haya comillas simples al inicio o final del archivo

### Error: "API did not become ready"

**Causa:** La API no puede conectarse a PostgreSQL o hay un error en el código

**Solución:**
- Verifica las credenciales de PostgreSQL
- Revisa los logs en `/tmp/api.log`
- Aumenta `EP_API_WAIT_SECONDS` a 60

## Enlaces Útiles

- [Azure App Service Documentation](https://docs.microsoft.com/azure/app-service/)
- [Python on Azure App Service](https://docs.microsoft.com/azure/app-service/quickstart-python)
