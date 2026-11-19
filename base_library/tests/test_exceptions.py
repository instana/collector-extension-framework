# (c) Copyright IBM Corp. 2026
"""
Tests for FR10: Exception Hierarchy and Error Handling.

This module validates the exception class hierarchy, inheritance relationships,
and error message formatting for the Extension Base Library.

Tests:
- test_base_exception_exists: Validates ExtensionBaseError base class
- test_config_exceptions: Validates configuration error hierarchy
- test_credentials_exceptions: Validates credentials error hierarchy
- test_metrics_exceptions: Validates metrics error hierarchy
- test_health_exceptions: Validates health reporting error hierarchy
- test_exception_inheritance: Validates inheritance chain
- test_exception_messages: Validates error message formatting

Spec Reference: docs/specs/extension-base-library.md#error-handling (lines 888-949)
"""

import pytest


class TestExceptionHierarchy:
    """Test suite for exception hierarchy validation (FR10)."""

    def test_base_exception_exists(self):
        """
        Test that ExtensionBaseError base exception class exists.

        Spec Reference: docs/specs/extension-base-library.md#exception-hierarchy
        - ExtensionBaseError (lines 893-895)

        Validates:
        - ExtensionBaseError class is defined
        - Inherits from Exception
        - Can be instantiated with a message
        - Message is accessible via str()

        Expected: Base exception class exists (TDD red phase - will fail)
        """
        # Import extension_base.exceptions module
        from extension_base import exceptions

        # Validate ExtensionBaseError exists
        assert hasattr(exceptions, "ExtensionBaseError"), (
            "ExtensionBaseError must be defined in exceptions module"
        )

        ExtensionBaseError = exceptions.ExtensionBaseError

        # Validate it's a class
        assert isinstance(ExtensionBaseError, type), (
            "ExtensionBaseError must be a class"
        )

        # Validate inheritance from Exception
        assert issubclass(ExtensionBaseError, Exception), (
            "ExtensionBaseError must inherit from Exception"
        )

        # Validate instantiation with message
        error_msg = "Test error message"
        error = ExtensionBaseError(error_msg)

        assert str(error) == error_msg, (
            "ExtensionBaseError message must be accessible via str()"
        )

        # Validate it can be raised and caught
        with pytest.raises(ExtensionBaseError) as exc_info:
            raise ExtensionBaseError("Test exception")

        assert "Test exception" in str(exc_info.value), (
            "Raised exception must contain the error message"
        )

    def test_config_exceptions(self):
        """
        Test that configuration exception classes exist and inherit correctly.

        Spec Reference: docs/specs/extension-base-library.md#exception-hierarchy
        - ConfigError (lines 897-899)
        - ConfigNotFoundError (lines 901-903)
        - ConfigParseError (lines 905-907)
        - ConfigValidationError (lines 909-911)

        Validates:
        - ConfigError base class exists
        - ConfigNotFoundError exists
        - ConfigParseError exists
        - ConfigValidationError exists
        - All inherit from ConfigError
        - ConfigError inherits from ExtensionBaseError

        Expected: Configuration exceptions exist (TDD red phase - will fail)
        """
        from extension_base import exceptions

        # Validate ConfigError exists
        assert hasattr(exceptions, "ConfigError"), (
            "ConfigError must be defined"
        )

        ConfigError = exceptions.ConfigError
        ExtensionBaseError = exceptions.ExtensionBaseError

        # Validate ConfigError inheritance
        assert issubclass(ConfigError, ExtensionBaseError), (
            "ConfigError must inherit from ExtensionBaseError"
        )

        # Validate specific config exceptions
        config_exception_classes = [
            "ConfigNotFoundError",
            "ConfigParseError",
            "ConfigValidationError",
        ]

        for exc_name in config_exception_classes:
            assert hasattr(exceptions, exc_name), f"{exc_name} must be defined"

            exc_class = getattr(exceptions, exc_name)

            # Validate inheritance from ConfigError
            assert issubclass(exc_class, ConfigError), (
                f"{exc_name} must inherit from ConfigError"
            )

            # Validate can be instantiated
            error = exc_class("Test error")
            assert str(error) == "Test error", (
                f"{exc_name} must support error messages"
            )

            # Validate can be caught as ConfigError
            with pytest.raises(ConfigError):
                raise exc_class("Test exception")

            # Validate can be caught as ExtensionBaseError
            with pytest.raises(ExtensionBaseError):
                raise exc_class("Test exception")

    def test_credentials_exceptions(self):
        """
        Test that credentials exception classes exist and inherit correctly.

        Spec Reference: docs/specs/extension-base-library.md#exception-hierarchy
        - CredentialsError (lines 913-915)
        - CredentialsFileNotFoundError (lines 917-919)
        - CredentialsParseError (lines 921-923)
        - CredentialRefNotFoundError (lines 925-927)
        - CredentialInvalidError (lines 929-931)

        Validates:
        - CredentialsError base class exists
        - CredentialsFileNotFoundError exists
        - CredentialsParseError exists
        - CredentialRefNotFoundError exists
        - CredentialInvalidError exists
        - All inherit from CredentialsError
        - CredentialsError inherits from ExtensionBaseError

        Expected: Credentials exceptions exist (TDD red phase - will fail)
        """
        from extension_base import exceptions

        # Validate CredentialsError exists
        assert hasattr(exceptions, "CredentialsError"), (
            "CredentialsError must be defined"
        )

        CredentialsError = exceptions.CredentialsError
        ExtensionBaseError = exceptions.ExtensionBaseError

        # Validate CredentialsError inheritance
        assert issubclass(CredentialsError, ExtensionBaseError), (
            "CredentialsError must inherit from ExtensionBaseError"
        )

        # Validate specific credentials exceptions
        creds_exception_classes = [
            "CredentialsFileNotFoundError",
            "CredentialsParseError",
            "CredentialRefNotFoundError",
            "CredentialInvalidError",
        ]

        for exc_name in creds_exception_classes:
            assert hasattr(exceptions, exc_name), f"{exc_name} must be defined"

            exc_class = getattr(exceptions, exc_name)

            # Validate inheritance from CredentialsError
            assert issubclass(exc_class, CredentialsError), (
                f"{exc_name} must inherit from CredentialsError"
            )

            # Validate can be instantiated
            error = exc_class("Test error")
            assert str(error) == "Test error", (
                f"{exc_name} must support error messages"
            )

            # Validate can be caught as CredentialsError
            with pytest.raises(CredentialsError):
                raise exc_class("Test exception")

            # Validate can be caught as ExtensionBaseError
            with pytest.raises(ExtensionBaseError):
                raise exc_class("Test exception")

    def test_metrics_exceptions(self):
        """
        Test that metrics exception classes exist and inherit correctly.

        Spec Reference: docs/specs/extension-base-library.md#exception-hierarchy
        - MetricsError (lines 933-935)
        - OTLPExportError (lines 937-939)

        Validates:
        - MetricsError base class exists
        - OTLPExportError exists
        - All inherit from MetricsError
        - MetricsError inherits from ExtensionBaseError

        Expected: Metrics exceptions exist (TDD red phase - will fail)
        """
        from extension_base import exceptions

        # Validate MetricsError exists
        assert hasattr(exceptions, "MetricsError"), (
            "MetricsError must be defined"
        )

        MetricsError = exceptions.MetricsError
        ExtensionBaseError = exceptions.ExtensionBaseError

        # Validate MetricsError inheritance
        assert issubclass(MetricsError, ExtensionBaseError), (
            "MetricsError must inherit from ExtensionBaseError"
        )

        # Validate specific metrics exceptions
        metrics_exception_classes = [
            "OTLPExportError",
        ]

        for exc_name in metrics_exception_classes:
            assert hasattr(exceptions, exc_name), f"{exc_name} must be defined"

            exc_class = getattr(exceptions, exc_name)

            # Validate inheritance from MetricsError
            assert issubclass(exc_class, MetricsError), (
                f"{exc_name} must inherit from MetricsError"
            )

            # Validate can be instantiated
            error = exc_class("Test error")
            assert str(error) == "Test error", (
                f"{exc_name} must support error messages"
            )

            # Validate can be caught as MetricsError
            with pytest.raises(MetricsError):
                raise exc_class("Test exception")

            # Validate can be caught as ExtensionBaseError
            with pytest.raises(ExtensionBaseError):
                raise exc_class("Test exception")

    def test_health_exceptions(self):
        """
        Test that health exception classes exist and inherit correctly.

        Spec Reference: docs/specs/extension-base-library.md#exception-hierarchy
        - HealthError (lines 941-943)
        - HealthFileWriteError (lines 945-947)

        Validates:
        - HealthError base class exists
        - HealthFileWriteError exists
        - All inherit from HealthError
        - HealthError inherits from ExtensionBaseError

        Expected: Health exceptions exist (TDD red phase - will fail)
        """
        from extension_base import exceptions

        # Validate HealthError exists
        assert hasattr(exceptions, "HealthError"), (
            "HealthError must be defined"
        )

        HealthError = exceptions.HealthError
        ExtensionBaseError = exceptions.ExtensionBaseError

        # Validate HealthError inheritance
        assert issubclass(HealthError, ExtensionBaseError), (
            "HealthError must inherit from ExtensionBaseError"
        )

        # Validate specific health exceptions
        health_exception_classes = [
            "HealthFileWriteError",
        ]

        for exc_name in health_exception_classes:
            assert hasattr(exceptions, exc_name), f"{exc_name} must be defined"

            exc_class = getattr(exceptions, exc_name)

            # Validate inheritance from HealthError
            assert issubclass(exc_class, HealthError), (
                f"{exc_name} must inherit from HealthError"
            )

            # Validate can be instantiated
            error = exc_class("Test error")
            assert str(error) == "Test error", (
                f"{exc_name} must support error messages"
            )

            # Validate can be caught as HealthError
            with pytest.raises(HealthError):
                raise exc_class("Test exception")

            # Validate can be caught as ExtensionBaseError
            with pytest.raises(ExtensionBaseError):
                raise exc_class("Test exception")

    def test_exception_inheritance(self):
        """
        Test that exception inheritance chain is correct.

        Spec Reference: docs/specs/extension-base-library.md#exception-hierarchy
        - Complete hierarchy (lines 890-948)

        Validates:
        - All custom exceptions inherit from ExtensionBaseError
        - Category exceptions (ConfigError, etc.) inherit from ExtensionBaseError
        - Specific exceptions inherit from their category
        - All exceptions ultimately inherit from Exception

        Expected: Inheritance chain is correct (TDD red phase - will fail)
        """
        from extension_base import exceptions

        ExtensionBaseError = exceptions.ExtensionBaseError

        # Define expected inheritance structure
        inheritance_map = {
            "ConfigError": ExtensionBaseError,
            "ConfigNotFoundError": exceptions.ConfigError,
            "ConfigParseError": exceptions.ConfigError,
            "ConfigValidationError": exceptions.ConfigError,
            "CredentialsError": ExtensionBaseError,
            "CredentialsFileNotFoundError": exceptions.CredentialsError,
            "CredentialsParseError": exceptions.CredentialsError,
            "CredentialRefNotFoundError": exceptions.CredentialsError,
            "CredentialInvalidError": exceptions.CredentialsError,
            "MetricsError": ExtensionBaseError,
            "OTLPExportError": exceptions.MetricsError,
            "HealthError": ExtensionBaseError,
            "HealthFileWriteError": exceptions.HealthError,
        }

        # Validate each exception's inheritance
        for exc_name, expected_parent in inheritance_map.items():
            assert hasattr(exceptions, exc_name), f"{exc_name} must be defined"

            exc_class = getattr(exceptions, exc_name)

            # Validate direct parent
            assert issubclass(exc_class, expected_parent), (
                f"{exc_name} must inherit from {expected_parent.__name__}"
            )

            # Validate ultimate parent is Exception
            assert issubclass(exc_class, Exception), (
                f"{exc_name} must ultimately inherit from Exception"
            )

            # Validate can be caught as ExtensionBaseError
            assert issubclass(exc_class, ExtensionBaseError), (
                f"{exc_name} must be catchable as ExtensionBaseError"
            )

    def test_exception_messages(self):
        """
        Test that exception messages are formatted correctly.

        Spec Reference: docs/specs/extension-base-library.md#exception-hierarchy
        - Exception base class (lines 893-895)

        Validates:
        - Exceptions accept string messages
        - Messages are preserved and accessible
        - Messages can include formatting
        - Multiple arguments are supported
        - Empty messages are handled

        Expected: Exception messages work correctly (TDD red phase - will fail)
        """
        from extension_base import exceptions

        # Test simple message
        error = exceptions.ExtensionBaseError("Simple error message")
        assert str(error) == "Simple error message", (
            "Simple messages must be preserved"
        )

        # Test formatted message
        error = exceptions.ConfigError(
            "Config file not found: /path/to/config.json"
        )
        assert "Config file not found" in str(error), (
            "Formatted messages must be preserved"
        )
        assert "/path/to/config.json" in str(error), (
            "Message details must be preserved"
        )

        # Test empty message
        error = exceptions.ExtensionBaseError()
        assert str(error) == "", "Empty messages must be handled"

        # Test message with special characters
        error = exceptions.ConfigParseError(
            "Invalid JSON: unexpected token '}' at line 42"
        )
        assert "Invalid JSON" in str(error), (
            "Messages with special characters must be preserved"
        )
        assert "line 42" in str(error), "Message details must be preserved"

        # Test exception can be raised and message retrieved
        try:
            raise exceptions.CredentialRefNotFoundError(
                "Credential 'api_key' not found in store"
            )
        except exceptions.CredentialRefNotFoundError as e:
            assert "api_key" in str(e), (
                "Exception message must be accessible after raising"
            )
            assert "not found in store" in str(e), (
                "Full message must be preserved"
            )


# Made with Bob
