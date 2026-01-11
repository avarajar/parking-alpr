.PHONY: help build up down logs test test-cov shell db-shell clean create-building

# Default target
help:
	@echo "Parking ALPR Microservice - Available commands:"
	@echo ""
	@echo "  make build         Build Docker images"
	@echo "  make up            Start all services"
	@echo "  make down          Stop all services"
	@echo "  make logs          View service logs"
	@echo "  make test          Run tests in Docker"
	@echo "  make test-cov      Run tests with coverage"
	@echo "  make shell         Open shell in API container"
	@echo "  make db-shell      Open PostgreSQL shell"
	@echo "  make clean         Remove containers and volumes"
	@echo "  make create-building  Create a test building"
	@echo ""

# Build Docker images
build:
	docker-compose build

# Start services
up:
	docker-compose up -d
	@echo ""
	@echo "Services started!"
	@echo "  API:  http://localhost:8000"
	@echo "  Docs: http://localhost:8000/docs"
	@echo ""

# Start services with logs
up-logs:
	docker-compose up

# Stop services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# Run tests in Docker
test:
	docker-compose run --rm api pytest -v

# Run tests with coverage
test-cov:
	docker-compose run --rm api pytest --cov=app --cov-report=term-missing

# Open shell in API container
shell:
	docker-compose exec api /bin/bash

# Open PostgreSQL shell
db-shell:
	docker-compose exec db psql -U postgres -d parking_db

# Clean everything
clean:
	docker-compose down -v --remove-orphans
	docker system prune -f

# Health check
health:
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "Service not running"

# Create a test building (returns API token)
create-building:
	@echo "Creating test building..."
	@curl -s -X POST "http://localhost:8000/admin/buildings?admin_token=change-me-in-production" \
		-H "Content-Type: application/json" \
		-d '{"name": "Test Building", "address": "123 Test St"}' | python3 -m json.tool

# List all buildings
list-buildings:
	@curl -s "http://localhost:8000/admin/buildings?admin_token=change-me-in-production" | python3 -m json.tool
