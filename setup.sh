#!/bin/bash

# Episcopio Setup Script
# Quick setup for development or production deployment

set -e  # Exit on error

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BOLD}================================${NC}"
echo -e "${BOLD}Episcopio Setup Script${NC}"
echo -e "${BOLD}================================${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "  Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    echo "  Please install Docker Compose from https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose is installed${NC}"

# Check if required ports are available
echo ""
echo "Checking if required ports are available..."
PORTS=(5432 6379 8000 8050)
PORTS_AVAILABLE=true

for PORT in "${PORTS[@]}"; do
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "${YELLOW}⚠ Port $PORT is already in use${NC}"
        PORTS_AVAILABLE=false
    else
        echo -e "${GREEN}✓ Port $PORT is available${NC}"
    fi
done

if [ "$PORTS_AVAILABLE" = false ]; then
    echo ""
    echo -e "${YELLOW}Warning: Some ports are in use. You may need to stop other services.${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create .env file if it doesn't exist
echo ""
if [ ! -f "infra/.env" ]; then
    echo "Creating .env file from template..."
    cp infra/.env.example infra/.env
    echo -e "${GREEN}✓ Created infra/.env${NC}"
    echo -e "${YELLOW}  Please edit infra/.env with your configuration${NC}"
else
    echo -e "${GREEN}✓ infra/.env already exists${NC}"
fi

# Create secrets.local.yaml if it doesn't exist
if [ ! -f "config/secrets.local.yaml" ]; then
    echo "Creating secrets.local.yaml from template..."
    cp config/secrets.sample.yaml config/secrets.local.yaml
    echo -e "${GREEN}✓ Created config/secrets.local.yaml${NC}"
    echo -e "${YELLOW}  Please edit config/secrets.local.yaml with your API keys${NC}"
else
    echo -e "${GREEN}✓ config/secrets.local.yaml already exists${NC}"
fi

# Ask if user wants to start services
echo ""
read -p "Do you want to build and start the services now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Building Docker images..."
    cd infra && docker-compose build
    
    echo ""
    echo "Starting services..."
    docker-compose up -d
    
    echo ""
    echo "Waiting for services to be ready..."
    sleep 10
    
    echo ""
    echo "Initializing database..."
    cd ..
    docker exec -i episcopio-db psql -U episcopio -d episcopio < db/schema/schema.sql 2>/dev/null || echo "Schema already exists"
    
    echo ""
    echo "Loading seed data..."
    docker exec -i episcopio-db psql -U episcopio -d episcopio < db/seeds/seed_entidades.sql 2>/dev/null || echo "Entidades already loaded"
    docker exec -i episcopio-db psql -U episcopio -d episcopio < db/seeds/seed_morbilidades.sql 2>/dev/null || echo "Morbilidades already loaded"
    
    echo ""
    echo -e "${BOLD}${GREEN}================================${NC}"
    echo -e "${BOLD}${GREEN}Setup Complete!${NC}"
    echo -e "${BOLD}${GREEN}================================${NC}"
    echo ""
    echo "Your Episcopio instance is running:"
    echo ""
    echo -e "  ${BOLD}Dashboard:${NC}  http://localhost:8050"
    echo -e "  ${BOLD}API:${NC}        http://localhost:8000"
    echo -e "  ${BOLD}API Docs:${NC}   http://localhost:8000/docs"
    echo ""
    echo "To view logs:    make logs"
    echo "To stop:         make down"
    echo "To restart:      make restart"
    echo ""
else
    echo ""
    echo -e "${YELLOW}Skipping service startup.${NC}"
    echo ""
    echo "To start services manually, run:"
    echo "  cd infra && docker-compose up -d"
    echo ""
    echo "Then initialize the database:"
    echo "  make init-db"
    echo "  make seed-db"
fi

echo ""
echo "For more information, see:"
echo "  - README.md"
echo "  - QUICKSTART.md"
echo "  - TESTING.md"
echo ""
