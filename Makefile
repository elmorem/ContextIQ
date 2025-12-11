.PHONY: help install dev-install clean format lint type-check test test-unit test-integration test-cov \
        docker-build docker-up docker-down docker-logs docker-clean \
        db-init db-create db-upgrade db-downgrade db-current db-history db-reset db-migrate db-revision db-seed \
        qdrant-init rabbitmq-init services-health \
        run-sessions run-memory run-procedural run-workers run-gateway \
        pre-commit-install pre-commit-run

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
YELLOW := \033[0;33m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "$(BLUE)ContextIQ Makefile Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-25s$(NC) %s\n", $$1, $$2}'

# ==================== Environment Setup ====================

install: ## Install production dependencies using uv
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	uv pip install -e .

dev-install: ## Install development dependencies using uv
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	uv pip install -e ".[dev]"
	@echo "$(GREEN)✓ Development dependencies installed$(NC)"

clean: ## Clean up cache and temporary files
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov coverage.xml .coverage
	@echo "$(GREEN)✓ Cleaned up$(NC)"

# ==================== Code Quality ====================

format: ## Format code with Black and Ruff
	@echo "$(BLUE)Formatting code...$(NC)"
	black services/ shared/ tests/
	ruff check --fix services/ shared/ tests/
	@echo "$(GREEN)✓ Code formatted$(NC)"

lint: ## Run linting checks
	@echo "$(BLUE)Running linting checks...$(NC)"
	ruff check services/ shared/ tests/
	@echo "$(GREEN)✓ Linting passed$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checks...$(NC)"
	mypy services/ shared/
	@echo "$(GREEN)✓ Type checking passed$(NC)"

pre-commit-install: ## Install pre-commit hooks
	@echo "$(BLUE)Installing pre-commit hooks...$(NC)"
	pre-commit install
	@echo "$(GREEN)✓ Pre-commit hooks installed$(NC)"

pre-commit-run: ## Run pre-commit on all files
	@echo "$(BLUE)Running pre-commit on all files...$(NC)"
	pre-commit run --all-files

# ==================== Testing ====================

test: ## Run all tests
	@echo "$(BLUE)Running all tests...$(NC)"
	pytest tests/ services/

test-unit: ## Run only unit tests
	@echo "$(BLUE)Running unit tests...$(NC)"
	pytest -m unit tests/ services/

test-integration: ## Run only integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	pytest -m integration tests/ services/

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest --cov --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/index.html$(NC)"

# ==================== Docker Commands ====================

docker-build: ## Build all Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose build
	@echo "$(GREEN)✓ Docker images built$(NC)"

docker-up: ## Start all services with Docker Compose
	@echo "$(BLUE)Starting services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "$(YELLOW)Run 'make docker-logs' to see logs$(NC)"

docker-down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

docker-logs: ## Show logs from all services
	docker-compose logs -f

docker-clean: ## Stop services and remove volumes
	@echo "$(RED)⚠ This will delete all data in volumes$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo "$(GREEN)✓ Services stopped and volumes removed$(NC)"; \
	fi

services-health: ## Check health status of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@docker-compose ps

# ==================== Database Migrations ====================

db-init: ## Initialize database and extensions
	@echo "$(BLUE)Initializing database...$(NC)"
	python scripts/db_init.py
	@echo "$(GREEN)✓ Database initialized$(NC)"

db-create: ## Create a new migration (usage: make db-create MESSAGE="add users table")
	@if [ -z "$(MESSAGE)" ]; then \
		echo "$(RED)Error: MESSAGE is required. Usage: make db-create MESSAGE='description'$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Creating new migration: $(MESSAGE)$(NC)"
	python scripts/db_migrate.py create "$(MESSAGE)"
	@echo "$(GREEN)✓ Migration created$(NC)"

db-upgrade: ## Upgrade database to latest (or specific revision: make db-upgrade REV=abc123)
	@echo "$(BLUE)Upgrading database...$(NC)"
	python scripts/db_migrate.py upgrade $(or $(REV),head)
	@echo "$(GREEN)✓ Database upgraded$(NC)"

db-downgrade: ## Downgrade database (usage: make db-downgrade REV=-1 or REV=abc123)
	@if [ -z "$(REV)" ]; then \
		echo "$(RED)Error: REV is required. Usage: make db-downgrade REV=-1$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Downgrading database...$(NC)"
	python scripts/db_migrate.py downgrade $(REV)
	@echo "$(GREEN)✓ Database downgraded$(NC)"

db-current: ## Show current database revision
	@echo "$(BLUE)Current database revision:$(NC)"
	python scripts/db_migrate.py current

db-history: ## Show migration history
	@echo "$(BLUE)Migration history:$(NC)"
	python scripts/db_migrate.py history

db-reset: ## Reset database to base and upgrade to latest
	@echo "$(RED)⚠ This will reset the database schema$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		python scripts/db_migrate.py downgrade base; \
		python scripts/db_migrate.py upgrade head; \
		echo "$(GREEN)✓ Database reset$(NC)"; \
	fi

# Legacy commands (deprecated, use new commands above)
db-migrate: db-upgrade ## Deprecated: Use db-upgrade instead
	@echo "$(YELLOW)⚠ db-migrate is deprecated, use db-upgrade instead$(NC)"

db-revision: ## Deprecated: Use db-create instead
	@echo "$(YELLOW)⚠ db-revision is deprecated, use db-create MESSAGE='...' instead$(NC)"
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)Error: MSG is required$(NC)"; \
		exit 1; \
	fi
	python scripts/db_migrate.py create "$(MSG)"

db-seed: ## Seed database with sample data
	@echo "$(BLUE)Seeding database...$(NC)"
	python scripts/seed_data.py
	@echo "$(GREEN)✓ Database seeded$(NC)"

# ==================== Service Initialization ====================

qdrant-init: ## Initialize Qdrant collections
	@echo "$(BLUE)Initializing Qdrant collections...$(NC)"
	python scripts/init_qdrant.py
	@echo "$(GREEN)✓ Qdrant collections initialized$(NC)"

rabbitmq-init: ## Initialize RabbitMQ queues and exchanges
	@echo "$(BLUE)Initializing RabbitMQ...$(NC)"
	python scripts/init_rabbitmq.py
	@echo "$(GREEN)✓ RabbitMQ initialized$(NC)"

# ==================== Run Individual Services (without Docker) ====================

run-sessions: ## Run Sessions service locally
	@echo "$(BLUE)Starting Sessions service on port 8001...$(NC)"
	cd services/sessions && uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

run-memory: ## Run Memory service locally
	@echo "$(BLUE)Starting Memory service on port 8002...$(NC)"
	cd services/memory && uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

run-procedural: ## Run Procedural Memory service locally
	@echo "$(BLUE)Starting Procedural Memory service on port 8003...$(NC)"
	cd services/procedural && uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload

run-workers: ## Run background workers locally
	@echo "$(BLUE)Starting workers...$(NC)"
	@echo "$(YELLOW)Starting extraction worker...$(NC)"
	cd services/workers/extraction && python -m app.worker &
	@echo "$(YELLOW)Starting consolidation worker...$(NC)"
	cd services/workers/consolidation && python -m app.worker &
	@echo "$(GREEN)✓ Workers started$(NC)"

run-gateway: ## Run API Gateway locally
	@echo "$(BLUE)Starting API Gateway on port 8000...$(NC)"
	cd services/api-gateway && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# ==================== Quick Setup Commands ====================

setup: dev-install pre-commit-install ## Complete development setup
	@echo "$(GREEN)✓ Development environment setup complete$(NC)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Copy .env.example to .env and configure"
	@echo "  2. Run 'make docker-up' to start services"
	@echo "  3. Run 'make db-migrate' to setup database"
	@echo "  4. Run 'make qdrant-init' to initialize Qdrant"

dev: docker-up db-migrate qdrant-init rabbitmq-init ## Start development environment
	@echo "$(GREEN)✓ Development environment ready$(NC)"
	@echo "$(YELLOW)Services available at:$(NC)"
	@echo "  API Gateway: http://localhost:8000"
	@echo "  Sessions: http://localhost:8001"
	@echo "  Memory: http://localhost:8002"
	@echo "  Procedural: http://localhost:8003"
	@echo "  RabbitMQ UI: http://localhost:15672"
	@echo "  Qdrant: http://localhost:6333/dashboard"

check: format lint type-check test ## Run all quality checks
	@echo "$(GREEN)✓ All checks passed$(NC)"
