# Extension Base Library

A Python library providing core functionality for Instana Custom Collector Extensions, including configuration management, OpenTelemetry metrics emission, health reporting, and lifecycle management.

## Overview

The Extension Base Library is an IBM-maintained Python library that abstracts common functionality required by all Collector Extensions. It is pre-installed in the Extension Runtime Container and provides a high-level API for extension developers.

### Key Features

- **Configuration Management**: Load and validate extension configuration with credential resolution
- **Metrics Emission**: Simplified OpenTelemetry OTLP/gRPC metric emission API
- **Health Reporting**: Container health status reporting for orchestration
- **Lifecycle Management**: Graceful shutdown handling and thread management
- **Structured Logging**: JSON-formatted logging for container environments
- **Type Safety**: Strong typing with Python type hints and Pydantic validation

## Installation

The library is pre-installed in the Extension Runtime Container at `/opt/instana/custom-collector/extension_base/`.

For local development:

```bash
cd base_library
uv sync
```

## Quick Start

```python
from extension_base import ExtensionBase

# Initialize the extension
extension = ExtensionBase()

# Define your collection function
def collect_metrics(endpoint, emitter):
    # Your collection logic here
    emitter.record_counter("my.metric", 1, {"status": "success"})

# Start the extension (blocks until shutdown signal)
extension.run(collect_metrics)
```

## Architecture

```
extension_base/
├── __init__.py                 # Public API exports
├── core.py                     # ExtensionBase main class
├── logging.py                  # Structured JSON logging
├── exceptions.py               # Custom exception hierarchy
├── config/
│   ├── loader.py               # Configuration loading
│   ├── models.py               # Pydantic data models
│   └── credentials.py          # Credentials management
├── metrics/
│   ├── emitter.py              # Metric emission API
│   └── otel_setup.py           # OpenTelemetry initialization
├── health/
│   └── reporter.py             # Health status reporting
└── lifecycle/
    └── manager.py              # Lifecycle and thread management
```

## Core Components

### Configuration Loader

Loads and validates extension configuration from JSON files and environment variables:

**Configuration Files**:
- `/opt/instana/custom-collector/config/extension-config.json` - Extension configuration
- `/opt/instana/custom-collector/config/credentials.json` - Credentials store

**Environment Variable Overrides**:
- `EXTENSION_CONFIG_FILE` - Custom config file path
- `EXTENSION_CREDENTIALS_FILE` - Custom credentials file path
- `EXTENSION_LOG_LEVEL` - Override log level
- `OTLP_ENDPOINT` - Override OTLP endpoint
- `CONTAINER_ID` - Container identifier
- `SUPERVISOR_ID` - Supervisor identifier

### Credentials Manager

Securely handles credential loading and resolution:

**Supported Credential Types**:
- Basic Authentication (username/password)
- Bearer Token
- API Key
- OAuth2 Client Credentials
- Client Certificates (TLS/mTLS)

### Metrics Emitter

Simplified API for emitting OpenTelemetry metrics:

**Metric Types**:
- **Counter**: Monotonically increasing values (e.g., request count)
- **Gauge**: Point-in-time values (e.g., memory usage)
- **Histogram**: Distribution of values (e.g., request duration)

**Resource Attributes** (automatically applied):
- `service.name` - Extension name
- `service.version` - Extension version
- `service.instance.id` - Container ID
- `container.id` - Container ID
- `instana.extension.id` - Extension ID
- `instana.supervisor.id` - Supervisor ID

### Health Reporter

Reports container health status for orchestration.

### Lifecycle Manager

Manages graceful shutdown and thread orchestration.

### Structured Logging

JSON-formatted logging for container environments:

**Environment Variables**:
- `INSTANA_LOG_LEVEL` - Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Error Handling

### Exception Hierarchy

```python
ExtensionBaseError                    # Base exception
├── ConfigError                       # Configuration errors
│   ├── ConfigNotFoundError          # Config file not found
│   ├── ConfigParseError             # JSON parsing failed
│   └── ConfigValidationError        # Schema validation failed
├── CredentialsError                  # Credentials errors
│   ├── CredentialsFileNotFoundError # Credentials file not found
│   ├── CredentialsParseError        # Credentials parsing failed
│   ├── CredentialRefNotFoundError   # Credential reference not found
│   └── CredentialInvalidError       # Invalid credential format
├── MetricsError                      # Metrics errors
│   └── OTLPExportError              # Metric export failed
└── HealthError                       # Health reporting errors
    └── HealthFileWriteError         # Health file write failed
```

## Testing

### Running Tests

```bash
# Run all tests
cd base_library
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src/extension_base --cov-report=html

# Run specific test file
uv run pytest tests/test_config_loader.py -v

# Run specific test
uv run pytest tests/test_config_loader.py::TestConfigLoader::test_load_valid_config -v
```

### Test Structure

```
tests/
├── conftest.py                      # Pytest fixtures
├── test_project_structure.py        # Project structure validation
├── test_exceptions.py               # Exception hierarchy tests
├── test_config_loader.py            # Configuration loading tests
├── test_credentials_manager.py      # Credentials management tests
├── test_metrics_emitter.py          # Metrics emission tests
├── test_health_reporter.py          # Health reporting tests
├── test_lifecycle_manager.py        # Lifecycle management tests
├── test_integration.py              # End-to-end integration tests
├── test_logging.py                  # Logging module tests
└── mocks/
    ├── mock_config.py               # Mock configuration files
    ├── mock_credentials.py          # Mock credentials store
    └── mock_otlp.py                 # Mock OTLP server
```

### Test Coverage Requirements

| Component | Minimum Coverage | Target Coverage |
|-----------|-----------------|-----------------|
| Overall | 80% | 90% |
| Core Components | 90% | 95% |
| Security-Critical | 100% | 100% |

**Security-Critical Components**:
- `config/credentials.py` - Credential handling
- `config/loader.py` - Credential resolution
- Exception handling - No credential leakage

### TDD Workflow

This project follows Test-Driven Development (TDD):

1. **RED Phase** ✅ - Tests created, implementation pending (current state)
2. **GREEN Phase** - Implement components to make tests pass
3. **REFACTOR Phase** - Improve code quality while maintaining passing tests

See [`tests/README.md`](tests/README.md) for details.

## Development

### Project Setup

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
cd base_library
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows
```

### Code Quality

```bash
# Run linter
uv run ruff check src/ tests/

# Run formatter
uv run ruff format src/ tests/

# Run type checker (if configured)
uv run mypy src/
```

### Project Configuration

See [`pyproject.toml`](pyproject.toml) for:
- Python version requirements (>=3.12)
- Dependencies (Pydantic, OpenTelemetry, psutil)
- Development dependencies (pytest, ruff, coverage)
- Test configuration (pytest, coverage)
- Code quality settings (ruff)

## Environment Variables

### Configuration

- `EXTENSION_CONFIG_FILE` - Path to extension-config.json (default: `/opt/instana/custom-collector/config/extension-config.json`)
- `EXTENSION_CREDENTIALS_FILE` - Path to credentials.json (default: `/opt/instana/custom-collector/config/credentials.json`)
- `EXTENSION_LOG_LEVEL` - Log level override (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `OTLP_ENDPOINT` - OTLP endpoint override
- `CONTAINER_ID` - Container identifier
- `SUPERVISOR_ID` - Supervisor identifier

### OpenTelemetry

- `OTEL_EXPORTER_OTLP_ENDPOINT` - OTLP endpoint
- `OTEL_EXPORTER_OTLP_PROTOCOL` - Protocol (grpc, http/protobuf, http/json)
- `OTEL_EXPORTER_OTLP_COMPRESSION` - Compression (gzip, none)
- `OTEL_METRIC_EXPORT_INTERVAL` - Export interval in milliseconds
- `OTEL_METRIC_EXPORT_TIMEOUT` - Export timeout in milliseconds

### Runtime

- `PYTHONUNBUFFERED=1` - Ensure immediate log output (set in container)
- `INSTANA_LOG_LEVEL` - Log level override

## References

- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/languages/python/)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
