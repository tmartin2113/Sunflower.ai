# Sunflower AI Education System - Makefile
# Simple commands for development and testing

.PHONY: help install run test clean docker-up docker-down setup-models quick-start

# Default target - show help
help:
	@echo "🌻 Sunflower AI - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "Quick Start:"
	@echo "  make quick-start    - One-command setup and run"
	@echo "  make run           - Run the application locally"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-up     - Start all services with Docker"
	@echo "  make docker-down   - Stop all Docker services"
	@echo "  make docker-logs   - View Docker logs"
	@echo "  make docker-clean  - Remove all containers and volumes"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install       - Install all dependencies"
	@echo "  make setup-models  - Download and configure AI models"
	@echo "  make create-profiles - Create demo family profiles"
	@echo ""
	@echo "Testing Commands:"
	@echo "  make test          - Run all tests"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-safety   - Run safety validation tests"
	@echo "  make test-coverage - Generate test coverage report"
	@echo ""
	@echo "Development Commands:"
	@echo "  make dev           - Run in development mode with hot reload"
	@echo "  make lint          - Run code linters"
	@echo "  make format        - Format code with Black"
	@echo "  make clean         - Clean up temporary files"
	@echo ""
	@echo "Production Commands:"
	@echo "  make build         - Build production release"
	@echo "  make package       - Create distribution package"
	@echo "  make validate      - Validate production readiness"
	@echo ""

# Quick start - one command to rule them all
quick-start: install setup-models
	@echo "🚀 Starting Sunflower AI..."
	@python run_local.py

# Run the application locally
run:
	@echo "🌻 Running Sunflower AI..."
	@python run_local.py

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	@pip install --quiet --upgrade pip
	@pip install -r requirements.txt
	@pip install -r requirements-test.txt 2>/dev/null || true
	@echo "✅ Dependencies installed"

# Docker commands
docker-up:
	@echo "🐳 Starting Docker services..."
	@docker-compose -f docker-compose.dev.yml up -d
	@echo "✅ Services started"
	@echo "📍 Web UI: http://localhost:8080"
	@echo "📍 Dashboard: http://localhost:8081"

docker-down:
	@echo "🛑 Stopping Docker services..."
	@docker-compose -f docker-compose.dev.yml down
	@echo "✅ Services stopped"

docker-logs:
	@docker-compose -f docker-compose.dev.yml logs -f

docker-clean: docker-down
	@echo "🧹 Cleaning Docker resources..."
	@docker-compose -f docker-compose.dev.yml down -v
	@docker system prune -f
	@echo "✅ Docker resources cleaned"

# Setup AI models
setup-models:
	@echo "🤖 Setting up AI models..."
	@mkdir -p models
	@ollama serve > /dev/null 2>&1 &
	@sleep 3
	@echo "📥 Pulling base models..."
	@ollama pull llama3.2:1b || echo "Model pull failed - continuing"
	@ollama pull llama3.2:3b || echo "Model pull failed - continuing"
	@echo "🔧 Creating Sunflower models..."
	@ollama create sunflower-kids -f modelfiles/sunflower-kids.modelfile || echo "Model creation failed"
	@ollama create sunflower-educator -f modelfiles/sunflower-educator.modelfile || echo "Model creation failed"
	@echo "✅ Models configured"

# Create demo profiles
create-profiles:
	@echo "👨‍👩‍👧‍👦 Creating demo family profiles..."
	@python -c "from run_local import SunflowerLocalRunner; runner = SunflowerLocalRunner(); runner.create_demo_profiles()"
	@echo "✅ Demo profiles created"

# Testing commands
test:
	@echo "🧪 Running all tests..."
	@python test_suite.py

test-unit:
	@echo "🧪 Running unit tests..."
	@pytest tests/unit/ -v

test-integration:
	@echo "🧪 Running integration tests..."
	@python test_openwebui_integration.py

test-safety:
	@echo "🛡️ Running safety validation..."
	@python tests/test_family_safety.py --comprehensive

test-coverage:
	@echo "📊 Generating coverage report..."
	@pytest --cov=. --cov-report=html --cov-report=term
	@echo "📍 Coverage report: htmlcov/index.html"

# Development commands
dev:
	@echo "👨‍💻 Starting development mode..."
	@export SUNFLOWER_ENV=development && \
	export SUNFLOWER_DEBUG=1 && \
	python run_local.py

lint:
	@echo "🔍 Running linters..."
	@flake8 . --max-line-length=100 --exclude=venv,__pycache__
	@pylint *.py --max-line-length=100 || true
	@mypy --ignore-missing-imports . || true

format:
	@echo "🎨 Formatting code..."
	@black --line-length 100 .
	@echo "✅ Code formatted"

clean:
	@echo "🧹 Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "*.log" -delete 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@rm -rf .coverage 2>/dev/null || true
	@rm -rf htmlcov 2>/dev/null || true
	@rm -rf temp 2>/dev/null || true
	@echo "✅ Cleanup complete"

# Production commands
build:
	@echo "🏗️ Building production release..."
	@python scripts/build_release.py
	@echo "✅ Build complete"

package:
	@echo "📦 Creating distribution package..."
	@mkdir -p dist
	@python scripts/create_package.py
	@echo "✅ Package created in dist/"

validate:
	@echo "✔️ Validating production readiness..."
	@python scripts/validate_production.py
	@echo "✅ Validation complete"

# Platform-specific targets
ifeq ($(OS),Windows_NT)
run-windows:
	@cmd /c run_sunflower.bat
else
    UNAME_S := $(shell uname -s)
    ifeq ($(UNAME_S),Linux)
run-linux:
	@bash scripts/run_linux.sh
    endif
    ifeq ($(UNAME_S),Darwin)
run-macos:
	@bash scripts/run_macos.sh
    endif
endif

# Git hooks
install-hooks:
	@echo "🔗 Installing Git hooks..."
	@cp scripts/pre-commit .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✅ Git hooks installed"

# Documentation
docs:
	@echo "📚 Generating documentation..."
	@python scripts/generate_docs.py
	@echo "✅ Documentation generated"

# Monitoring
monitor:
	@echo "📊 Starting monitoring dashboard..."
	@python scripts/metrics_dashboard.py --port 8888

# Benchmarks
benchmark:
	@echo "⚡ Running performance benchmarks..."
	@pytest tests/benchmarks/ --benchmark-only

# Database operations
db-init:
	@echo "🗄️ Initializing database..."
	@python scripts/init_database.py

db-migrate:
	@echo "🔄 Running database migrations..."
	@python scripts/migrate_database.py

db-backup:
	@echo "💾 Backing up database..."
	@python scripts/backup_database.py

# CI/CD
ci: lint test
	@echo "✅ CI checks passed"

cd-staging:
	@echo "🚀 Deploying to staging..."
	@python scripts/deploy_staging.py

cd-production:
	@echo "🚀 Deploying to production..."
	@python scripts/deploy_production.py

# Special targets
.SILENT: help
.DEFAULT_GOAL := help
