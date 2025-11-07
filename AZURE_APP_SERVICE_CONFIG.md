# Azure App Service Deployment Configuration

## Overview

This document explains the configuration files used for deploying Episcopio to Azure App Service.

## Configuration Files

### 1. startup.sh (REQUIRED for Linux)

The `startup.sh` script is the primary startup file for Azure App Service Linux deployments. It:

- Activates the Azure Oryx pre-built virtual environment (`antenv`)
- Installs all dependencies from requirements.txt files
- Starts the API service using Gunicorn with Uvicorn workers
- Starts the Dashboard service using Gunicorn
- Monitors both processes and handles graceful shutdown

**Key features:**
- Uses Azure's pre-built `antenv` instead of creating a new virtual environment
- Falls back to other virtual environment sources if `antenv` is not available
- Runs both services in production mode with Gunicorn
- Provides comprehensive logging (separate access and error logs)
- Includes health checks for the API service
- Monitors processes and restarts on failure

### 2. azure-webapp.json (REQUIRED)

This file contains the ARM template parameters for Azure Web App creation:

```json
{
  "kind": "linux",
  "siteConfig": {
    "linuxFxVersion": "PYTHON|3.11",
    "appCommandLine": "bash startup.sh"
  }
}
```

**Key settings:**
- `kind: "linux"` - Specifies Linux-based App Service
- `linuxFxVersion: "PYTHON|3.11"` - Python runtime version
- `appCommandLine: "bash startup.sh"` - Command to start the application

### 3. web.config (NOT USED for Linux)

**Important:** The `web.config` file is **only used by Windows-based Azure App Services**. 

For Python applications on Azure, you should use **Linux-based App Services**, which:
- Do NOT use `web.config`
- Configure startup via `appCommandLine` in Portal or azure-webapp.json
- Set environment variables via Portal > Configuration > Application settings

The `web.config` file is included in this repository for documentation purposes only. If you're using Linux-based App Service (recommended), this file will be ignored.

## Azure Portal Configuration

### Required Application Settings

Configure these in Azure Portal under **Configuration > Application settings**:

| Setting | Value | Description |
|---------|-------|-------------|
| `WEBSITES_PORT` | `8050` | Port for Dashboard (publicly exposed) |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` | Enable Oryx build |
| `EP_POSTGRES_HOST` | `<your-db>.postgres.database.azure.com` | PostgreSQL server |
| `EP_POSTGRES_USER` | `<username>` | Database user |
| `EP_POSTGRES_PASSWORD` | `<password>` | Database password |
| `EP_POSTGRES_DATABASE` | `episcopio` | Database name |
| `EP_POSTGRES_PORT` | `5432` | PostgreSQL port |
| `EP_REDIS_URL` | `redis://<host>:6379/0` | Redis connection string |
| `EP_API_URL` | `http://localhost:8000` | API URL for Dashboard |
| `EP_SECURITY_CORS_ALLOWED_ORIGINS` | `https://your-domain.com` | Allowed CORS origins |

### Startup Command

Set in Azure Portal under **Configuration > General settings > Startup Command**:

```bash
bash startup.sh
```

Or configure via Azure CLI:

```bash
az webapp config set \
  --name <app-name> \
  --resource-group <resource-group> \
  --startup-file "bash startup.sh"
```

## Deployment Process

### How Azure Oryx Works

When you deploy to Azure App Service Linux with Python:

1. **Build Phase (Oryx)**:
   - Detects Python application
   - Creates a virtual environment called `antenv`
   - Installs dependencies from requirements.txt into `antenv`
   - Compiles and optimizes packages

2. **Deployment Phase**:
   - Extracts `antenv` to application directory
   - Copies application files
   - Sets up environment

3. **Startup Phase**:
   - Runs `startup.sh` script
   - Script activates `antenv` (no need to create new venv)
   - Starts application services

### Common Issues and Solutions

#### Issue: "No such file or directory: venv/bin/python3"

**Cause:** Script tries to create a new venv instead of using Oryx's `antenv`

**Solution:** Use the corrected `startup.sh` that checks for `antenv` first

#### Issue: Services not starting

**Cause:** Missing Gunicorn or incorrect command

**Solution:** 
- Ensure gunicorn is in requirements.txt
- Use `gunicorn main:app` for FastAPI
- Use `gunicorn app:app.server` for Dash

#### Issue: Port not accessible

**Cause:** Wrong WEBSITES_PORT or service not binding to correct port

**Solution:**
- Set `WEBSITES_PORT=8050` (Dashboard port)
- Ensure Dashboard binds to `0.0.0.0:8050`
- API runs on `localhost:8000` (internal only)

## Architecture

```
Internet
   ↓
Azure Load Balancer
   ↓
App Service (port 8050) ← WEBSITES_PORT
   ↓
┌─────────────────────────────────┐
│  Linux Container                │
│                                 │
│  ┌─────────────┐  localhost    │
│  │ Dashboard   │ ←──────────┐  │
│  │ (port 8050) │            │  │
│  └─────────────┘            │  │
│         ↓                    │  │
│     requests to              │  │
│     EP_API_URL               │  │
│         ↓                    │  │
│  ┌─────────────┐            │  │
│  │ API         │ ───────────┘  │
│  │ (port 8000) │               │
│  └─────────────┘               │
│                                 │
│  Started by: startup.sh        │
│  Environment: antenv            │
└─────────────────────────────────┘
```

## Testing Locally

To test the startup script locally (simulating Azure):

```bash
# Create a mock antenv for testing
python3 -m venv antenv

# Run the startup script
bash startup.sh
```

## Monitoring

### Viewing Logs in Azure

```bash
# Stream application logs
az webapp log tail --name <app-name> --resource-group <resource-group>

# Download logs
az webapp log download --name <app-name> --resource-group <resource-group>
```

### Log Files

The startup script creates separate log files:

- `/tmp/api-access.log` - API access log
- `/tmp/api-error.log` - API error log  
- `/tmp/dashboard-access.log` - Dashboard access log
- `/tmp/dashboard-error.log` - Dashboard error log

## References

- [Azure App Service Python documentation](https://docs.microsoft.com/azure/app-service/configure-language-python)
- [Azure Oryx build system](https://github.com/microsoft/Oryx)
- [Gunicorn deployment](https://docs.gunicorn.org/en/stable/deploy.html)
- [FastAPI deployment](https://fastapi.tiangolo.com/deployment/server-workers/)
