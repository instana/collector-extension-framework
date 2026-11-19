# (c) Copyright IBM Corp. 2026
"""
Exception hierarchy for Extension Base Library.

All custom exceptions inherit from ExtensionBaseError which inherits
from the built-in Exception, allowing callers to catch at any level
of specificity.
"""


class ExtensionBaseError(Exception):
    """Base exception for all Extension Base Library errors."""

    pass


class ConfigError(ExtensionBaseError):
    """Base class for configuration errors."""

    pass


class ConfigNotFoundError(ConfigError):
    """Configuration file not found."""

    pass


class ConfigParseError(ConfigError):
    """Configuration JSON parsing failed."""

    pass


class ConfigValidationError(ConfigError):
    """Configuration schema validation failed."""

    pass


class CredentialsError(ExtensionBaseError):
    """Base class for credentials errors."""

    pass


class CredentialsFileNotFoundError(CredentialsError):
    """Credentials file not found."""

    pass


class CredentialsParseError(CredentialsError):
    """Credentials JSON parsing failed."""

    pass


class CredentialRefNotFoundError(CredentialsError):
    """Credential reference not found in store."""

    pass


class CredentialInvalidError(CredentialsError):
    """Credential missing required fields."""

    pass


class MetricsError(ExtensionBaseError):
    """Base class for metrics errors."""

    pass


class OTLPExportError(MetricsError):
    """OTLP metric export failed."""

    pass


class HealthError(ExtensionBaseError):
    """Base class for health reporting errors."""

    pass


class HealthFileWriteError(HealthError):
    """Failed to write health status file."""

    pass
