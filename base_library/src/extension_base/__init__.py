# (c) Copyright IBM Corp. 2026
"""
Extension Base Library for Instana Custom Collector Framework.

Provides core functionality for building extensions:
- Configuration loading and validation
- Credential management
- Structured JSON logging
- OpenTelemetry metrics emission via OTLP
- HTTP health status reporting
- Lifecycle and graceful shutdown management

Quick start::

    from extension_base.core import ExtensionBase

    extension = ExtensionBase()

    def collect(endpoint, emitter):
        emitter.record_counter("my.metric", 1)

    extension.run(collect)
"""

from importlib.metadata import version

from extension_base.config.loader import ConfigLoader
from extension_base.config.models import (
    Configuration,
    CredentialEntry,
    Endpoint,
    ExtensionConfig,
    OTLPConfiguration,
)
from extension_base.core import ExtensionBase
from extension_base.exceptions import (
    ConfigError,
    ConfigNotFoundError,
    ConfigParseError,
    ConfigValidationError,
    CredentialInvalidError,
    CredentialRefNotFoundError,
    CredentialsError,
    CredentialsFileNotFoundError,
    CredentialsParseError,
    ExtensionBaseError,
    HealthError,
    HealthFileWriteError,
    MetricsError,
    OTLPExportError,
)
from extension_base.health.reporter import HealthReporter
from extension_base.lifecycle.manager import LifecycleManager
from extension_base.logging import (
    JSONFormatter,
    get_logger,
    set_thread_context,
    setup_logging,
)
from extension_base.metrics.emitter import MetricsEmitter
from extension_base.metrics.otel_setup import (
    configure_otlp_exporter,
    create_meter_provider,
    setup_otel,
)

__version__: str = version("extension-base")

__all__ = [
    # Core
    "ExtensionBase",
    # Configuration
    "ConfigLoader",
    "ExtensionConfig",
    "Configuration",
    "OTLPConfiguration",
    "Endpoint",
    "CredentialEntry",
    # Logging
    "JSONFormatter",
    "setup_logging",
    "get_logger",
    "set_thread_context",
    # Metrics
    "MetricsEmitter",
    "setup_otel",
    "create_meter_provider",
    "configure_otlp_exporter",
    # Health
    "HealthReporter",
    # Lifecycle
    "LifecycleManager",
    # Exceptions
    "ExtensionBaseError",
    "ConfigError",
    "ConfigNotFoundError",
    "ConfigParseError",
    "ConfigValidationError",
    "CredentialsError",
    "CredentialsFileNotFoundError",
    "CredentialsParseError",
    "CredentialRefNotFoundError",
    "CredentialInvalidError",
    "MetricsError",
    "OTLPExportError",
    "HealthError",
    "HealthFileWriteError",
]
