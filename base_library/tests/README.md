# Extension Base Library - Test Suite

**Status**: TDD Red Phase - Tests Only (No Implementation)  
**Python Version**: 3.12+  
**Test Framework**: pytest  
**Package Manager**: uv

---

## Overview

This is the comprehensive test suite for the Extension Base Library, following Test-Driven Development (TDD) principles. All tests are written **before** implementation to ensure specification compliance and high code quality.

### Current Phase: 🔴 RED (Tests Fail)

All tests in this suite are expected to **FAIL** initially because no implementation code exists yet. This is the correct TDD red phase.

---

## Project Structure

```
base_library/
├── pyproject.toml              # uv project configuration with pytest settings
├── README.md                   # This file
├── src/
│   └── extension_base/         # Source code (empty - TDD placeholder)
│       ├── __init__.py
│       ├── config/             # Configuration loader module
│       ├── metrics/            # Metrics emitter module
│       ├── health/             # Health reporter module
│       └── lifecycle/          # Lifecycle manager module
└── tests/                      # Test suite (107 test functions)
    ├── conftest.py             # Shared pytest fixtures
    ├── test_project_structure.py
    ├── test_exceptions.py
    ├── test_config_loader.py
    ├── test_credentials_manager.py
    ├── test_metrics_emitter.py
    ├── test_health_reporter.py
    ├── test_lifecycle_manager.py
    ├── test_extension_base.py
    ├── test_integration.py
    ├── test_logging.py
    └── mocks/                  # Mock objects for testing
        ├── mock_otlp.py
        ├── mock_config.py
        └── mock_credentials.py
```

---

## Installation

### Prerequisites

- Python 3.12 or higher
- uv package manager

### Setup

```bash
# Navigate to project directory
cd base_library

# Install dependencies with uv
uv sync

# Verify installation
uv run pytest --version
```

---

## Running Tests

### Run All Tests (Expected: All FAIL in red phase)

```bash
uv run pytest
```

### Run with Coverage Report

```bash
uv run pytest --cov --cov-report=html
```

Expected coverage: **0%** (no implementation exists yet)

### Run Specific Test Module

```bash
# Configuration loader tests
uv run pytest tests/test_config_loader.py -v

# Exception hierarchy tests
uv run pytest tests/test_exceptions.py -v

# Integration tests
uv run pytest tests/test_integration.py -v
```

### Run Tests by Marker

```bash
# Unit tests only
uv run pytest -m unit

# Integration tests only
uv run pytest -m integration
```

---

## Test Execution Expectations

### TDD Red Phase (Current)

- ✅ **All tests should FAIL** - This is correct!
- ✅ **0% code coverage** - No implementation exists
- ✅ **Fast execution** - Tests fail immediately (< 5 seconds)

### TDD Green Phase (After Implementation)

- ✅ **All tests should PASS**
- ✅ **80%+ overall coverage, 90%+ core components**
- ✅ **< 30 seconds execution time**

---

## Test Coverage Requirements

| Component | Coverage Target | Test Count |
|-----------|----------------|------------|
| Configuration Loader | 90% | 15 tests |
| Credentials Manager | 90% | 14 tests |
| Metrics Emitter | 90% | 20 tests |
| Health Reporter | 90% | 14 tests |
| Lifecycle Manager | 90% | 15 tests |
| Integration Tests | 80% | 12 tests |
| Exception Hierarchy | 100% | 7 tests |
| Logging Module | 80% | 7 tests |
| Project Structure | 80% | 3 tests |
| **Total** | **80%+ overall** | **107 tests** |

---

## Test Organization

Tests are organized by functional requirement (FR1-FR10):

- **FR1**: Project Structure Tests
- **FR2**: Configuration Loader Tests
- **FR3**: Credentials Manager Tests
- **FR4**: Metrics Emitter Tests
- **FR5**: Health Reporter Tests
- **FR6**: Lifecycle Manager Tests
- **FR7**: Integration Tests
- **FR8**: Mock Objects and Fixtures
- **FR9**: Logging Module Tests
- **FR10**: Exception Hierarchy Tests

---

## Development Workflow

### 1. Red Phase (Current)

```bash
# Write tests first
uv run pytest  # All tests FAIL ✓

# Verify 0% coverage
uv run pytest --cov  # 0% coverage ✓
```

### 2. Green Phase (Next)

```bash
# Implement code to make tests pass
# Run tests frequently
uv run pytest  # Tests gradually PASS

# Check coverage
uv run pytest --cov  # Coverage increases
```

### 3. Refactor Phase

```bash
# Improve code quality
# Tests still pass
uv run pytest  # All tests PASS ✓

# Maintain coverage
uv run pytest --cov  # 80%+ coverage ✓
```

---

## Troubleshooting

### Tests Not Discovered

```bash
# Verify test discovery
uv run pytest --collect-only

# Check pytest configuration
cat pyproject.toml | grep -A 10 "tool.pytest"
```

### Import Errors

```bash
# Ensure uv environment is activated
uv sync

# Verify Python path
uv run python -c "import sys; print(sys.path)"
```

### Coverage Not Working

```bash
# Install coverage plugin
uv add --dev pytest-cov

# Run with verbose output
uv run pytest --cov --cov-report=term-missing -v
```

---

## References

- [pytest Documentation](https://docs.pytest.org/)
- [uv Documentation](https://github.com/astral-sh/uv)
