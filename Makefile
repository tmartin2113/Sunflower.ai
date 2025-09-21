# ============================================================================
# Sunflower AI Education System - Makefile
# Version: 6.2 - Production Ready (No ANSI Colors)
# Purpose: Simple commands for development, testing, and production
# Fixed: Removed all ANSI codes for universal compatibility
# ============================================================================

.PHONY: help install run test clean docker-up docker-down setup-models quick-start \
        dev lint format build package validate test-unit test-integration test-safety \
        test-coverage install-hooks docs monitor benchmark db-init db-migrate db-backup \
        ci cd-staging cd-production

# Default target - show help
help:
	@echo "========================================"
	@echo "    Sunflower AI - Available Commands"
	@echo "========================================"
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

# ============================================================================
# QUICK START COMMANDS
# ============================================================================

# Quick start - one command to rule them all
quick-start: install setup-models
	@echo "[INFO] Starting Sunflower AI..."
	@python run_local.py

# Run the application locally
run:
	@echo "[INFO] Running Sunflower AI..."
	@python run_local.py

# ============================================================================
# INSTALLATION COMMANDS
# ============================================================================

# Install dependencies
install:
	@echo "[INFO] Installing dependencies..."
	@pip install --quiet --upgrade pip
	@pip install -r requirements.txt
	@pip install -r requirements-test.txt 2>/dev/null || true
	@echo "[OK] Dependencies installed"

# Setup AI models
setup-models:
	@echo "[INFO] Setting up AI models..."
	@mkdir -p models
	@ollama serve > /dev/null 2>&1 &
	@sleep 3
	@echo "[INFO] Pulling base models..."
	@ollama pull llama3.2:1b || echo "[WARNING] Model pull failed - continuing"
	@ollama pull llama3.2:3b || echo "[WARNING] Model pull failed - continuing"
	@echo "[INFO] Creating Sunflower models..."
	@ollama create sunflower-kids -f modelfiles/sunflower-kids.modelfile || echo "[WARNING] Model creation failed"
	@ollama create sunflower-educator -f modelfiles/sunflower-educator.modelfile || echo "[WARNING] Model creation failed"
	@echo "[OK] Models configured"

# Create demo profiles
create-profiles:
	@echo "[INFO] Creating demo family profiles..."
	@python -c "from run_local import SunflowerLocalRunner; runner = SunflowerLocalRunner(); runner.create_demo_profiles()"
	@echo "[OK] Demo profiles created"

# ============================================================================
# DOCKER COMMANDS
# ============================================================================

# Start Docker services
docker-up:
	@echo "[INFO] Starting Docker services..."
	@docker-compose -f docker-compose.dev.yml up -d
	@echo "[OK] Services started"
	@echo "Web UI: http://localhost:8080"
	@echo "Dashboard: http://localhost:8081"

# Stop Docker services
docker-down:
	@echo "[INFO] Stopping Docker services..."
	@docker-compose -f docker-compose.dev.yml down
	@echo "[OK] Services stopped"

# View Docker logs
docker-logs:
	@docker-compose -f docker-compose.dev.yml logs -f

# Clean Docker resources
docker-clean: docker-down
	@echo "[INFO] Cleaning Docker resources..."
	@docker-compose -f docker-compose.dev.yml down -v
	@docker system prune -f
	@echo "[OK] Docker resources cleaned"

# ============================================================================
# TESTING COMMANDS
# ============================================================================

# Run all tests
test:
	@echo "[INFO] Running all tests..."
	@python test_suite.py

# Run unit tests
test-unit:
	@echo "[INFO] Running unit tests..."
	@pytest tests/unit/ -v

# Run integration tests
test-integration:
	@echo "[INFO] Running integration tests..."
	@python test_openwebui_integration.py

# Run safety validation
test-safety:
	@echo "[INFO] Running safety validation..."
	@python tests/test_family_safety.py --comprehensive

# Generate coverage report
test-coverage:
	@echo "[INFO] Generating coverage report..."
	@pytest --cov=. --cov-report=html --cov-report=term
	@echo "[OK] Coverage report: htmlcov/index.html"

# ============================================================================
# DEVELOPMENT COMMANDS
# ============================================================================

# Run in development mode
dev:
	@echo "[INFO] Starting development mode..."
	@export SUNFLOWER_ENV=development && \
	export SUNFLOWER_DEBUG=1 && \
	python run_local.py

# Run code linters
lint:
	@echo "[INFO] Running linters..."
	@echo "  Checking with flake8..."
	@flake8 . --max-line-length=100 --exclude=venv,__pycache__
	@echo "  Checking with pylint..."
	@pylint *.py --max-line-length=100 || true
	@echo "  Checking with mypy..."
	@mypy --ignore-missing-imports . || true
	@echo "[OK] Linting complete"

# Format code
format:
	@echo "[INFO] Formatting code..."
	@black --line-length 100 .
	@echo "[OK] Code formatted"

# Clean up temporary files
clean:
	@echo "[INFO] Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "*.log" -delete 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@rm -rf .coverage 2>/dev/null || true
	@rm -rf htmlcov 2>/dev/null || true
	@rm -rf temp 2>/dev/null || true
	@echo "[OK] Cleanup complete"

# ============================================================================
# PRODUCTION COMMANDS
# ============================================================================

# Build production release
build:
	@echo "[INFO] Building production release..."
	@python scripts/build_release.py
	@echo "[OK] Build complete"

# Create distribution package
package:
	@echo "[INFO] Creating distribution package..."
	@mkdir -p dist
	@python scripts/create_package.py
	@echo "[OK] Package created in dist/"

# Validate production readiness
validate:
	@echo "[INFO] Validating production readiness..."
	@python scripts/validate_production.py
	@echo "[OK] Validation complete"

# ============================================================================
# PLATFORM-SPECIFIC TARGETS
# ============================================================================

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

# ============================================================================
# GIT AND DOCUMENTATION
# ============================================================================

# Install Git hooks
install-hooks:
	@echo "[INFO] Installing Git hooks..."
	@cp scripts/pre-commit .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "[OK] Git hooks installed"

# Generate documentation
docs:
	@echo "[INFO] Generating documentation..."
	@python scripts/generate_docs.py
	@echo "[OK] Documentation generated"

# ============================================================================
# MONITORING AND BENCHMARKS
# ============================================================================

# Start monitoring dashboard
monitor:
	@echo "[INFO] Starting monitoring dashboard..."
	@python scripts/metrics_dashboard.py --port 8888

# Run performance benchmarks
benchmark:
	@echo "[INFO] Running performance benchmarks..."
	@pytest tests/benchmarks/ --benchmark-only

# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

# Initialize database
db-init:
	@echo "[INFO] Initializing database..."
	@python scripts/init_database.py

# Run database migrations
db-migrate:
	@echo "[INFO] Running database migrations..."
	@python scripts/migrate_database.py

# Backup database
db-backup:
	@echo "[INFO] Backing up database..."
	@python scripts/backup_database.py

# ============================================================================
# CI/CD COMMANDS
# ============================================================================

# Run CI checks
ci: lint test
	@echo "[OK] CI checks passed"

# Deploy to staging
cd-staging:
	@echo "[INFO] Deploying to staging..."
	@python scripts/deploy_staging.py

# Deploy to production
cd-production:
	@echo "[INFO] Deploying to production..."
	@python scripts/deploy_production.py

# ============================================================================
# SPECIAL TARGETS
# ============================================================================

.SILENT: help
.DEFAULT_GOAL := help
