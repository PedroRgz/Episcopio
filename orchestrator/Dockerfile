# ⚠️ DEPRECATED: Use Azure deployment instead. See AZURE_DEPLOYMENT.md
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Run the scheduler
CMD ["python", "orchestrator/scheduler.py"]
