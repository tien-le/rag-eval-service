.PHONY: help install set-env dev staging prod test test-unit test-integration test-e2e test-acceptance lint format type-check check all init-db clean docker-build docker-build-env docker-run docker-run-env docker-logs docker-stop docker-compose-up docker-compose-down docker-compose-logs migrate migrate-upgrade migrate-downgrade migrate-revision migrate-history migrate-current

# Variables
DOCKER_COMPOSE ?= docker compose
PYTHON ?= python
UV ?= uv
ENV ?= dev

# Default target
.DEFAULT_GOAL := help

# Installation
install:
	@echo "Installing uv..."
	@pip install uv
	@echo "Syncing dependencies..."
	@uv sync

# Environment setup
set-env:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make set-env ENV=dev|staging|production|test"; \
		exit 1; \
	fi
	@if [ "$(ENV)" != "dev" ] && [ "$(ENV)" != "development" ] && [ "$(ENV)" != "staging" ] && [ "$(ENV)" != "production" ] && [ "$(ENV)" != "prod" ] && [ "$(ENV)" != "test" ]; then \
		echo "ENV is not valid. Must be one of: dev, development, staging, production, prod, test"; \
		exit 1; \
	fi
	@echo "Setting APP_ENV to $(ENV)"
	@export APP_ENV=$(ENV)

# Run server commands
prod:
	@echo "Starting server in production environment"
	@APP_ENV=production $(UV) run uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop uvloop

staging:
	@echo "Starting server in staging environment"
	@APP_ENV=staging $(UV) run uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop uvloop

dev:
	@echo "Starting server in development environment"
	@APP_ENV=dev $(UV) run uvicorn app.main:app --reload --port 8000 --loop uvloop

# Test commands
test:
	@echo "Running all tests"
	@APP_ENV=test $(UV) run pytest

test-unit:
	@echo "Running unit tests"
	@APP_ENV=test $(UV) run pytest tests/unit -v

# --no-cov : disables coverage checking for the integration tests,
# preventing failures when coverage is below 80%
test-integration:
	@echo "Running integration tests"
	@APP_ENV=test $(UV) run pytest tests/integration -v --no-cov

test-e2e:
	@echo "Running end-to-end tests"
	@APP_ENV=test $(UV) run pytest tests/e2e -v --no-cov

test-acceptance:
	@echo "Running acceptance tests"
	@APP_ENV=test $(UV) run pytest tests/acceptance -v --no-cov

test-coverage:
	@echo "Running tests with coverage"
	@APP_ENV=test $(UV) run pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml

# Code quality
lint:
	@echo "Running ruff linter"
	@$(UV) run ruff check .

format:
	@echo "Formatting code with ruff"
	@$(UV) run ruff format .

type-check:
	@echo "Running mypy type checker"
	@$(UV) run mypy app/

check: lint type-check
	@echo "Running all checks (lint + type-check)"

# All-in-one command: initialize DB, format, lint, and test
all: init-db format lint test
	@echo ""
	@echo "=========================================="
	@echo "✅ All tasks completed successfully!"
	@echo "=========================================="
	@echo "  ✓ Database initialized"
	@echo "  ✓ Code formatted"
	@echo "  ✓ Code linted"
	@echo "  ✓ Tests passed"
	@echo "=========================================="

# Database initialization and migrations
init-db:
	@echo "Initializing database..."
	@echo "Step 1: Waiting for database to be ready..."
	@APP_ENV=$(ENV) $(UV) run python app/tools/backend_pre_start.py
	@echo "Step 2: Running database migrations..."
	@APP_ENV=$(ENV) $(UV) run python -m alembic -c app/alembic.ini upgrade head
	@echo "Step 3: Creating initial data..."
	@APP_ENV=$(ENV) $(UV) run python app/tools/initial_data.py
	@echo "Database initialization complete!"

# Database migrations
migrate:
	@echo "Running Alembic migrations"
	@APP_ENV=$(ENV) $(UV) run python -m alembic -c app/alembic.ini upgrade head

migrate-upgrade:
	@if [ -z "$(REVISION)" ]; then \
		echo "Running Alembic upgrade head"; \
		APP_ENV=$(ENV) $(UV) run python -m alembic -c app/alembic.ini upgrade head; \
	else \
		echo "Running Alembic upgrade to $(REVISION)"; \
		APP_ENV=$(ENV) $(UV) run python -m alembic -c app/alembic.ini upgrade $(REVISION); \
	fi

migrate-downgrade:
	@if [ -z "$(REVISION)" ]; then \
		echo "REVISION is required. Usage: make migrate-downgrade REVISION=-1"; \
		exit 1; \
	fi
	@echo "Running Alembic downgrade to $(REVISION)"
	@APP_ENV=$(ENV) $(UV) run python -m alembic -c app/alembic.ini downgrade $(REVISION)

migrate-revision:
	@if [ -z "$(MESSAGE)" ]; then \
		echo "MESSAGE is required. Usage: make migrate-revision MESSAGE='description'"; \
		exit 1; \
	fi
	@echo "Creating new Alembic revision: $(MESSAGE)"
	@APP_ENV=$(ENV) $(UV) run python -m alembic -c app/alembic.ini revision --autogenerate -m "$(MESSAGE)"

migrate-history:
	@echo "Showing Alembic migration history"
	@APP_ENV=$(ENV) $(UV) run python -m alembic -c app/alembic.ini history

migrate-current:
	@echo "Showing current Alembic revision"
	@APP_ENV=$(ENV) $(UV) run python -m alembic -c app/alembic.ini current

# Cleanup
clean:
	@echo "Cleaning up generated files"
	@rm -rf .venv
	@rm -rf __pycache__
	@rm -rf .pytest_cache
	@rm -rf .coverage
	@rm -rf htmlcov
	@rm -rf coverage.xml
	@find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name ".coverage" -delete

# Docker build commands
docker-build:
	@echo "Building Docker image"
	@docker build -t fastapi-template .

docker-build-env:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make docker-build-env ENV=dev|staging|production"; \
		exit 1; \
	fi
	@if [ "$(ENV)" != "dev" ] && [ "$(ENV)" != "development" ] && [ "$(ENV)" != "staging" ] && [ "$(ENV)" != "production" ] && [ "$(ENV)" != "prod" ]; then \
		echo "ENV is not valid. Must be one of: dev, development, staging, production, prod"; \
		exit 1; \
	fi
	@echo "Building Docker image for $(ENV) environment"
	@docker build --build-arg APP_ENV=$(ENV) -t fastapi-template:$(ENV) .

# Docker run commands
docker-run:
	@ENV_FILE=configs/dev.env; \
	if [ ! -f $$ENV_FILE ]; then \
		echo "Environment file $$ENV_FILE not found. Please create it."; \
		exit 1; \
	fi; \
	echo "Starting Docker containers with default (dev) environment"; \
	APP_ENV=dev $(DOCKER_COMPOSE) --env-file $$ENV_FILE up -d --build

docker-run-env:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make docker-run-env ENV=dev|staging|production"; \
		exit 1; \
	fi
	@if [ "$(ENV)" != "dev" ] && [ "$(ENV)" != "development" ] && [ "$(ENV)" != "staging" ] && [ "$(ENV)" != "production" ] && [ "$(ENV)" != "prod" ]; then \
		echo "ENV is not valid. Must be one of: dev, development, staging, production, prod"; \
		exit 1; \
	fi
	@ENV_FILE=configs/$(ENV).env; \
	if [ ! -f $$ENV_FILE ]; then \
		echo "Environment file $$ENV_FILE not found. Please create it."; \
		exit 1; \
	fi; \
	echo "Starting Docker containers for $(ENV) environment"; \
	APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file $$ENV_FILE up -d --build

docker-logs:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make docker-logs ENV=dev|staging|production"; \
		exit 1; \
	fi
	@if [ "$(ENV)" != "dev" ] && [ "$(ENV)" != "development" ] && [ "$(ENV)" != "staging" ] && [ "$(ENV)" != "production" ] && [ "$(ENV)" != "prod" ]; then \
		echo "ENV is not valid. Must be one of: dev, development, staging, production, prod"; \
		exit 1; \
	fi
	@ENV_FILE=configs/$(ENV).env; \
	if [ ! -f $$ENV_FILE ]; then \
		echo "Environment file $$ENV_FILE not found. Please create it."; \
		exit 1; \
	fi; \
	echo "Showing logs for $(ENV) environment"; \
	APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file $$ENV_FILE logs -f

docker-stop:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make docker-stop ENV=dev|staging|production"; \
		exit 1; \
	fi
	@if [ "$(ENV)" != "dev" ] && [ "$(ENV)" != "development" ] && [ "$(ENV)" != "staging" ] && [ "$(ENV)" != "production" ] && [ "$(ENV)" != "prod" ]; then \
		echo "ENV is not valid. Must be one of: dev, development, staging, production, prod"; \
		exit 1; \
	fi
	@ENV_FILE=configs/$(ENV).env; \
	if [ ! -f $$ENV_FILE ]; then \
		echo "Environment file $$ENV_FILE not found. Please create it."; \
		exit 1; \
	fi; \
	echo "Stopping Docker containers for $(ENV) environment"; \
	APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file $$ENV_FILE down

# Docker Compose commands for the entire stack
docker-compose-up:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make docker-compose-up ENV=dev|staging|production"; \
		exit 1; \
	fi
	@if [ "$(ENV)" != "dev" ] && [ "$(ENV)" != "development" ] && [ "$(ENV)" != "staging" ] && [ "$(ENV)" != "production" ] && [ "$(ENV)" != "prod" ]; then \
		echo "ENV is not valid. Must be one of: dev, development, staging, production, prod"; \
		exit 1; \
	fi
	@ENV_FILE=configs/$(ENV).env; \
	if [ ! -f $$ENV_FILE ]; then \
		echo "Environment file $$ENV_FILE not found. Please create it."; \
		exit 1; \
	fi; \
	echo "Starting entire Docker Compose stack for $(ENV) environment"; \
	APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file $$ENV_FILE up -d

docker-compose-down:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make docker-compose-down ENV=dev|staging|production"; \
		exit 1; \
	fi
	@ENV_FILE=configs/$(ENV).env; \
	if [ ! -f $$ENV_FILE ]; then \
		echo "Environment file $$ENV_FILE not found. Please create it."; \
		exit 1; \
	fi; \
	echo "Stopping entire Docker Compose stack for $(ENV) environment"; \
	APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file $$ENV_FILE down

docker-compose-logs:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make docker-compose-logs ENV=dev|staging|production"; \
		exit 1; \
	fi
	@ENV_FILE=configs/$(ENV).env; \
	if [ ! -f $$ENV_FILE ]; then \
		echo "Environment file $$ENV_FILE not found. Please create it."; \
		exit 1; \
	fi; \
	echo "Showing logs for entire Docker Compose stack ($(ENV) environment)"; \
	APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file $$ENV_FILE logs -f

docker-compose-restart:
	@if [ -z "$(ENV)" ]; then \
		echo "ENV is not set. Usage: make docker-compose-restart ENV=dev|staging|production"; \
		exit 1; \
	fi
	@ENV_FILE=configs/$(ENV).env; \
	if [ ! -f $$ENV_FILE ]; then \
		echo "Environment file $$ENV_FILE not found. Please create it."; \
		exit 1; \
	fi; \
	echo "Restarting Docker Compose stack for $(ENV) environment"; \
	APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file $$ENV_FILE restart

# Help
help:
	@echo "Retrieval Augmented Generation (RAG) Evaluation Server - Makefile Commands"
	@echo "=========================================================================="
	@echo ""
	@echo "Installation & Setup:"
	@echo "  install                    Install dependencies using uv"
	@echo "  set-env ENV=<env>          Set environment (dev|staging|production|test)"
	@echo ""
	@echo "All-in-One:"
	@echo "  all                        Initialize DB, format, lint, and test (recommended for first-time setup)"
	@echo ""
	@echo "Run Server:"
	@echo "  dev                        Run server in development mode (reload enabled)"
	@echo "  staging                    Run server in staging environment"
	@echo "  prod                       Run server in production environment"
	@echo ""
	@echo "Testing:"
	@echo "  test                       Run all tests"
	@echo "  test-unit                  Run unit tests only"
	@echo "  test-integration           Run integration tests only"
	@echo "  test-e2e                   Run end-to-end tests only"
	@echo "  test-acceptance            Run acceptance tests only"
	@echo "  test-coverage              Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint                       Run ruff linter"
	@echo "  format                     Format code with ruff"
	@echo "  type-check                 Run mypy type checker"
	@echo "  check                      Run all checks (lint + type-check)"
	@echo ""
	@echo "Database:"
	@echo "  init-db                    Initialize database (wait for DB, run migrations, create initial data)"
	@echo "  migrate                    Run all pending migrations (upgrade head)"
	@echo "  migrate-upgrade [REVISION=<rev>]  Upgrade to specific revision (default: head)"
	@echo "  migrate-downgrade REVISION=<rev> Downgrade to specific revision"
	@echo "  migrate-revision MESSAGE='<msg>'  Create new migration with message"
	@echo "  migrate-history            Show migration history"
	@echo "  migrate-current           Show current migration revision"
	@echo ""
	@echo "Docker Build:"
	@echo "  docker-build               Build default Docker image"
	@echo "  docker-build-env ENV=<env> Build Docker image for specific environment"
	@echo ""
	@echo "Docker Run:"
	@echo "  docker-run                 Run containers with default (dev) environment"
	@echo "  docker-run-env ENV=<env>   Run containers for specific environment"
	@echo "  docker-logs ENV=<env>      View logs from running containers"
	@echo "  docker-stop ENV=<env>      Stop and remove containers"
	@echo ""
	@echo "Docker Compose Stack:"
	@echo "  docker-compose-up ENV=<env>     Start entire stack (all services)"
	@echo "  docker-compose-down ENV=<env>   Stop entire stack"
	@echo "  docker-compose-logs ENV=<env>   View logs from all services"
	@echo "  docker-compose-restart ENV=<env> Restart entire stack"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean                      Remove generated files (venv, cache, coverage)"
	@echo ""
	@echo "Examples:"
	@echo "  make dev"
	@echo "  make test"
	@echo "  make docker-compose-up ENV=dev"
	@echo "  make migrate-revision MESSAGE='add user table'"
	@echo "  make docker-logs ENV=dev"