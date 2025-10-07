.PHONY: help build up down logs clean test init-db seed-db

help: ## Show this help message
	@echo "Episcopio - Makefile commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build all Docker images
	cd infra && docker-compose build

up: ## Start all services
	cd infra && docker-compose up -d

down: ## Stop all services
	cd infra && docker-compose down

logs: ## Show logs from all services
	cd infra && docker-compose logs -f

logs-api: ## Show API logs
	cd infra && docker-compose logs -f api

logs-dashboard: ## Show dashboard logs
	cd infra && docker-compose logs -f dashboard

logs-scheduler: ## Show scheduler logs
	cd infra && docker-compose logs -f scheduler

restart: down up ## Restart all services

clean: ## Stop and remove all containers, volumes, and networks
	cd infra && docker-compose down -v

init-db: ## Initialize database schema
	docker exec -i episcopio-db psql -U episcopio -d episcopio < db/schema/schema.sql

seed-db: ## Load seed data
	docker exec -i episcopio-db psql -U episcopio -d episcopio < db/seeds/seed_entidades.sql
	docker exec -i episcopio-db psql -U episcopio -d episcopio < db/seeds/seed_morbilidades.sql

setup: build up init-db seed-db ## Full setup: build, start, initialize and seed database
	@echo ""
	@echo "✓ Setup complete!"
	@echo ""
	@echo "Dashboard: http://localhost:8050"
	@echo "API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

test: ## Run tests and validation
	@echo "Running configuration validation..."
	python -c "import yaml; yaml.safe_load(open('config/settings.yaml'))"
	python -c "import yaml; yaml.safe_load(open('config/secrets.sample.yaml'))"
	python -c "import yaml; yaml.safe_load(open('analytics/reglas/alertas.yaml'))"
	@echo "✓ Configuration files are valid"

lint: ## Run linting on Python code
	@echo "Running flake8..."
	flake8 api/ dashboard/ analytics/ etl/ ingesta/ orchestrator/ config/ --count --statistics || true

status: ## Show status of all services
	cd infra && docker-compose ps

shell-db: ## Open PostgreSQL shell
	docker exec -it episcopio-db psql -U episcopio -d episcopio

shell-api: ## Open API container shell
	docker exec -it episcopio-api /bin/bash

shell-dashboard: ## Open dashboard container shell
	docker exec -it episcopio-dashboard /bin/bash
