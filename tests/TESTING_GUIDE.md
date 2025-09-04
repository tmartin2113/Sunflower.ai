# Sunflower AI Professional System - Testing Guide

## Version 6.2 - Production Testing Documentation

### Table of Contents
1. [Overview](#overview)
2. [Test Environment Setup](#test-environment-setup)
3. [Running Tests Locally](#running-tests-locally)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Test Categories](#test-categories)
6. [Critical Validation Points](#critical-validation-points)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The Sunflower AI testing framework ensures 100% reliability for our family-focused K-12 STEM education system. Our tests validate:

- **Safety**: 100% content filtering effectiveness for children
- **Performance**: Sub-3-second response times on minimum hardware
- **Usability**: 95%+ setup success rate for non-technical parents
- **Cross-Platform**: Identical experience on Windows and macOS
- **Integration**: Seamless Open WebUI integration

### Key Testing Principles

1. **No Placeholder Code**: All tests use production-ready implementations
2. **Family-First**: Tests simulate real family usage scenarios
3. **Safety-Critical**: Child safety tests have zero tolerance for failures
4. **Hardware-Aware**: Tests validate all hardware configurations

---

## Test Environment Setup

### Prerequisites

#### System Requirements
- **RAM**: Minimum 8GB (16GB recommended for full test suite)
- **Storage**: 10GB free space
- **OS**: Windows 10+, macOS 11+, or Ubuntu 20.04+
- **Python**: 3.11 or higher
- **Docker**: Latest stable version

#### Required Software

```bash
# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Install Docker (Ubuntu)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Chrome/Chromium for Selenium tests
# Ubuntu:
sudo apt-get install chromium-browser chromium-chromedriver
# macOS:
brew install --cask chromium
# Windows:
# Download from https://www.chromium.org/
```

### Clone Repository with Open WebUI

```bash
# Clone main repository
git clone https://github.com/your-org/sunflower-ai.git
cd sunflower-ai

# Initialize submodules (includes Open WebUI)
git submodule update --init --recursive

# Verify Open WebUI is present
ls -la open-webui/
```

### Set Up Test Models

```bash
# Start Ollama service
ollama serve &

# Pull base models
ollama pull llama3.2:7b
ollama pull llama3.2:3b
ollama pull llama3.2:1b

# Create Sunflower models
ollama create sunflower-kids -f modelfiles/sunflower-kids.modelfile
ollama create sunflower-educator -f modelfiles/sunflower-educator.modelfile

# Verify models
ollama list
```

---

## Running Tests Locally

### Quick Start - Run All Tests

```bash
# Run complete test suite
python test_suite.py

# Run with verbose output
python test_suite.py -v

# Run with coverage report
pytest . --cov=. --cov-report=html
```

### Platform-Specific Tests

#### Windows Testing

```batch
:: Run Windows-specific tests
pytest tests\test_windows.py -v

:: Test launcher
cd launchers\windows
test_launcher.bat

:: Test partition detection
python tests\test_partition_windows.py
```

#### macOS Testing

```bash
# Run macOS-specific tests
pytest tests/test_macos.py -v

# Test launcher
cd launchers/macos
chmod +x test_launcher.sh
./test_launcher.sh

# Test partition detection
python tests/test_partition_macos.py
```

### Test Categories

#### 1. Unit Tests
```bash
# Core functionality
pytest tests/unit/ -v

# Specific components
pytest tests/unit/test_safety_filter.py -v
pytest tests/unit/test_profile_system.py -v
pytest tests/unit/test_model_selector.py -v
```

#### 2. Integration Tests
```bash
# Open WebUI integration
python test_openwebui_integration.py

# Full system integration
pytest tests/integration/ -v

# With Docker services
docker-compose -f docker-compose.test.yml up -d
pytest tests/integration/ -v
docker-compose -f docker-compose.test.yml down
```

#### 3. Safety Tests (Critical)
```bash
# Comprehensive safety validation
python tests/test_family_safety.py --comprehensive

# Validate 100% filtering accuracy
python tests/validate_safety_filter.py --required-accuracy 1.0

# Age-appropriate content tests
python tests/test_age_appropriate.py --all-age-groups

# Generate safety report
python scripts/generate_safety_report.py --output safety-report.html
```

#### 4. Performance Tests
```bash
# Run benchmarks
pytest tests/benchmarks/ --benchmark-only

# Stress testing with concurrent users
pytest tests/test_load.py -v -m stress

# Memory profiling
python tests/test_memory.py --profile

# Response time validation
python tests/test_response_times.py --max-time 3.0
```

#### 5. End-to-End Tests
```bash
# Complete user journey
python tests/test_e2e.py

# Family setup simulation
python tests/test_family_setup.py --simulate-parent

# Multi-child household test
python tests/test_multi_child.py --children 3
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

The automated pipeline runs on:
- Every push to `main` and `develop`
- All pull requests
- Daily at 2 AM UTC
- Manual trigger via workflow dispatch

### Pipeline Stages

1. **Code Quality** (5 min)
   - Black formatter check
   - Flake8 linting
   - MyPy type checking
   - Bandit security scan
   - Dependency vulnerability check

2. **Platform Tests** (15 min parallel)
   - Windows-specific tests
   - macOS-specific tests
   - Linux baseline tests

3. **Core Tests** (20 min)
   - Unit tests
   - Integration tests
   - Performance benchmarks
   - Safety validation

4. **Open WebUI Integration** (10 min)
   - API integration
   - UI automation
   - Model switching
   - Session persistence

5. **Manufacturing Validation** (5 min)
   - Partition creation
   - Device authentication
   - Checksum verification

### Triggering Manual Tests

```bash
# Via GitHub CLI
gh workflow run test.yml -f test_type=safety

# Via GitHub UI
# Navigate to Actions → Sunflower AI Test Suite → Run workflow
```

---

## Critical Validation Points

### 🔴 Must-Pass Requirements

These tests have **zero tolerance** for failure:

#### 1. Child Safety (100% Required)
```python
# Test configuration
SAFETY_FILTER_ACCURACY = 1.0  # 100% requirement

# Validation command
python tests/validate_safety.py --zero-tolerance
```

#### 2. Setup Success Rate (≥95% Required)
```python
# Test configuration
SETUP_SUCCESS_RATE = 0.95  # 95% requirement

# Validation command
python tests/test_setup_success.py --min-rate 0.95
```

#### 3. Response Time (<3s Required)
```python
# Test configuration
MAX_RESPONSE_TIME = 3.0  # 3 second maximum

# Validation command
python tests/test_performance.py --max-response 3.0
```

#### 4. Profile Switching (<1s Required)
```python
# Test configuration
MAX_SWITCH_TIME = 1.0  # 1 second maximum

# Validation command
python tests/test_profile_switch.py --max-time 1.0
```

### Test Metrics Dashboard

View real-time metrics during test execution:

```bash
# Start metrics server
python scripts/metrics_server.py --port 8080

# Open browser to http://localhost:8080/metrics
```

---

## Test Data Management

### Creating Test Profiles

```python
# scripts/create_test_data.py
from test_utils import create_test_family

# Create a test family
family = create_test_family(
    parent_name="TestParent",
    children=[
        {"name": "Child1", "age": 7},
        {"name": "Child2", "age": 12},
        {"name": "Child3", "age": 16}
    ]
)
```

### Test Conversations

Test conversations are stored in `test_data/conversations/`:
- `safe_prompts.json` - Age-appropriate STEM questions
- `unsafe_prompts.json` - Content that should be filtered
- `edge_cases.json` - Boundary testing scenarios

### Backup and Restore

```bash
# Backup test environment
python scripts/backup_test_env.py --output backups/test_backup.tar.gz

# Restore test environment
python scripts/restore_test_env.py --input backups/test_backup.tar.gz
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Docker Services Not Starting
```bash
# Check Docker status
docker ps -a

# View logs
docker-compose -f docker-compose.test.yml logs

# Reset Docker
docker system prune -a
docker-compose -f docker-compose.test.yml up --build
```

#### 2. Model Loading Failures
```bash
# Check Ollama status
ollama list

# Re-create models
ollama rm sunflower-kids
ollama create sunflower-kids -f modelfiles/sunflower-kids.modelfile

# Verify model files
sha256sum modelfiles/*.modelfile
```

#### 3. Selenium WebDriver Issues
```bash
# Update ChromeDriver
pip install --upgrade selenium
sudo apt-get update && sudo apt-get install chromium-chromedriver

# Check version compatibility
chromium --version
chromedriver --version
```

#### 4. Permission Errors on Partition Tests
```bash
# Linux/macOS
sudo chmod +x scripts/test_partitions.sh
sudo python tests/test_partitions.py

# Windows (Run as Administrator)
python tests\test_partitions.py
```

#### 5. Memory Issues During Tests
```bash
# Increase test timeout
pytest --timeout=300

# Run tests in smaller batches
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/performance/ -v

# Monitor memory usage
python scripts/monitor_memory.py &
pytest tests/ -v
```

### Debug Mode

Enable detailed debugging output:

```bash
# Set environment variables
export SUNFLOWER_DEBUG=1
export SUNFLOWER_LOG_LEVEL=DEBUG

# Run tests with debug output
python test_suite.py --debug

# Generate debug report
python scripts/generate_debug_report.py --output debug-report.txt
```

### Getting Help

1. **Check Logs**: `logs/test_results.log`
2. **Run Diagnostics**: `python scripts/run_diagnostics.py`
3. **Generate Report**: `python scripts/generate_test_report.py`
4. **Contact**: File an issue with the debug report attached

---

## Test Reporting

### Generate HTML Report
```bash
python scripts/generate_test_report.py \
  --input-dir test-results/ \
  --output report.html \
  --format html
```

### Generate PDF Report
```bash
python scripts/generate_test_report.py \
  --input-dir test-results/ \
  --output report.pdf \
  --format pdf
```

### View Coverage Report
```bash
# Generate coverage report
pytest --cov=. --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov\index.html  # Windows
```

---

## Continuous Monitoring

### Production Validation

After deployment, validate the production system:

```bash
# Run production smoke tests
python tests/smoke_tests.py --env production

# Validate device integrity
python scripts/validate_device.py /dev/disk2

# Monitor first 100 user setups
python scripts/monitor_setup_success.py --count 100
```

### Metrics Collection

Key metrics are automatically collected:
- Setup completion rate
- Average response times
- Safety filter triggers
- Model selection distribution
- Error rates by platform

View metrics dashboard:
```bash
python scripts/metrics_dashboard.py --port 8080
```

---

## Summary

The Sunflower AI test suite ensures production readiness through comprehensive validation:

✅ **100% child safety guarantee**  
✅ **Cross-platform compatibility**  
✅ **Performance requirements met**  
✅ **Non-technical parent friendly**  
✅ **Manufacturing quality assured**  

For any testing questions or issues, refer to the debug logs or file an issue with the complete test report attached.
