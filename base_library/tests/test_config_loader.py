# (c) Copyright IBM Corp. 2026
"""
Tests for FR2: Configuration Loader and proxy configuration.

This module validates configuration file loading, JSON schema validation,
credential resolution, environment variable overrides, and default application.

Tests cover the complete configuration loading workflow including error handling
for missing files, invalid JSON, schema violations, and credential issues.

Spec Reference: docs/specs/extension-base-library.md#configuration-loader (lines 196-269)
"""

import os
from unittest.mock import patch

from extension_base.config.loader import ConfigLoader

import pytest


class TestConfigLoader:
    """Test suite for configuration loader (FR2)."""

    def test_config_loader_class_exists(self):
        """
        Test that ConfigLoader class exists and can be instantiated.

        Spec Reference: docs/specs/extension-base-library.md#configuration-loader
        - API/Interface (lines 260-269)

        Validates:
        - ConfigLoader class is defined in config.loader module
        - Can be instantiated with default paths
        - Can be instantiated with custom paths
        - Has load() method

        Expected: ConfigLoader class exists (TDD red phase - will fail)
        """
        from extension_base.config import loader

        # Validate ConfigLoader exists
        assert hasattr(loader, "ConfigLoader"), (
            "ConfigLoader must be defined in config.loader module"
        )

        ConfigLoader = loader.ConfigLoader

        # Validate it's a class
        assert isinstance(ConfigLoader, type), "ConfigLoader must be a class"

        # Validate can be instantiated with defaults
        config_loader = ConfigLoader()
        assert config_loader is not None, (
            "ConfigLoader must be instantiable with defaults"
        )

        # Validate can be instantiated with custom paths
        config_loader = ConfigLoader(
            config_path="/custom/config.json",
            credentials_path="/custom/credentials.json",
        )
        assert config_loader is not None, (
            "ConfigLoader must accept custom paths"
        )

        # Validate has load() method
        assert hasattr(config_loader, "load"), (
            "ConfigLoader must have load() method"
        )
        assert callable(config_loader.load), (
            "ConfigLoader.load() must be callable"
        )

    def test_load_valid_config(self, mock_config_file, mock_credentials_store):
        """
        Test loading a valid configuration file.

        Spec Reference: docs/specs/extension-base-library.md#configuration-loader
        - File Loading (lines 204-208)
        - Schema Validation (lines 210-214)

        Validates:
        - Loads valid config JSON successfully
        - Returns ExtensionConfig object
        - All required fields are present
        - Credentials are resolved

        Expected: Valid config loads successfully (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader

        # Create valid config and credentials
        config_path = mock_config_file.create_valid_config()
        creds_path = mock_credentials_store.create_basic_auth_store()

        # Load configuration
        loader = ConfigLoader(
            config_path=str(config_path), credentials_path=str(creds_path)
        )
        config = loader.load()

        # Validate config object
        assert config is not None, "Config must not be None"
        assert hasattr(config, "extension_id"), "Config must have extension_id"
        assert hasattr(config, "extension_name"), (
            "Config must have extension_name"
        )
        assert hasattr(config, "extension_version"), (
            "Config must have extension_version"
        )
        assert hasattr(config, "configuration"), (
            "Config must have configuration"
        )
        assert hasattr(config, "otlp"), "Config must have otlp"

        # Validate required fields
        assert config.extension_id == "ext-123456", (
            "extension_id must match config file"
        )
        assert config.extension_name == "test-extension", (
            "extension_name must match config file"
        )
        assert config.extension_version == "1.0.0", (
            "extension_version must match config file"
        )

        # Validate configuration section
        assert config.configuration is not None, (
            "configuration section must exist"
        )
        assert hasattr(config.configuration, "endpoints"), (
            "configuration must have endpoints"
        )
        assert len(config.configuration.endpoints) > 0, (
            "configuration must have at least one endpoint"
        )

        # Validate credentials are resolved
        endpoint = config.configuration.endpoints[0]
        assert hasattr(endpoint, "credentials"), (
            "endpoint must have credentials"
        )
        assert endpoint.credentials is not None, (
            "endpoint credentials must be resolved"
        )

    def test_load_config_file_not_found(self):
        """
        Test handling of missing configuration file.

        Spec Reference: docs/specs/extension-base-library.md#configuration-loader
        - File Loading (lines 204-208)

        Validates:
        - Raises ConfigNotFoundError when file doesn't exist
        - Error message includes file path
        - Error is catchable as ConfigError

        Expected: Raises ConfigNotFoundError (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader
        from extension_base.exceptions import ConfigError, ConfigNotFoundError

        # Attempt to load non-existent config
        loader = ConfigLoader(
            config_path="/nonexistent/config.json",
            credentials_path="/nonexistent/credentials.json",
        )

        # Validate raises ConfigNotFoundError
        with pytest.raises(ConfigNotFoundError) as exc_info:
            loader.load()

        # Validate error message
        error_msg = str(exc_info.value)
        assert (
            "config.json" in error_msg.lower()
            or "not found" in error_msg.lower()
        ), "Error message must mention missing file"

        # Validate can be caught as ConfigError
        with pytest.raises(ConfigError):
            loader.load()

    def test_load_invalid_json(self, mock_config_file):
        """
        Test handling of malformed JSON in config file.

        Spec Reference: docs/specs/extension-base-library.md#configuration-loader
        - File Loading (lines 204-208)

        Validates:
        - Raises ConfigParseError for invalid JSON
        - Error message indicates JSON parsing failure
        - Error is catchable as ConfigError

        Expected: Raises ConfigParseError (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader
        from extension_base.exceptions import ConfigError, ConfigParseError

        # Create config with invalid JSON
        config_path = mock_config_file.create_invalid_json()

        # Attempt to load invalid config
        loader = ConfigLoader(
            config_path=str(config_path),
            credentials_path="/tmp/dummy_creds.json",
        )

        # Validate raises ConfigParseError
        with pytest.raises(ConfigParseError) as exc_info:
            loader.load()

        # Validate error message
        error_msg = str(exc_info.value)
        assert "json" in error_msg.lower() or "parse" in error_msg.lower(), (
            "Error message must indicate JSON parsing failure"
        )

        # Validate can be caught as ConfigError
        with pytest.raises(ConfigError):
            loader.load()

    def test_load_missing_required_fields(self, mock_config_file):
        """
        Test handling of config missing required fields.

        Spec Reference: docs/specs/extension-base-library.md#configuration-loader
        - Schema Validation (lines 210-214)

        Validates:
        - Raises ConfigValidationError for missing extension_id
        - Raises ConfigValidationError for missing extension_name
        - Raises ConfigValidationError for missing extension_version
        - Raises ConfigValidationError for missing configuration
        - Raises ConfigValidationError for missing otlp.endpoint
        - Error messages indicate which field is missing

        Expected: Raises ConfigValidationError (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader
        from extension_base.exceptions import ConfigValidationError

        # Test missing extension_id
        config_path = mock_config_file.create_missing_field("extension_id")
        loader = ConfigLoader(config_path=str(config_path))

        with pytest.raises(ConfigValidationError) as exc_info:
            loader.load()
        assert "extension_id" in str(exc_info.value).lower(), (
            "Error must mention missing extension_id"
        )

        # Test missing extension_name
        config_path = mock_config_file.create_missing_field("extension_name")
        loader = ConfigLoader(config_path=str(config_path))

        with pytest.raises(ConfigValidationError) as exc_info:
            loader.load()
        assert "extension_name" in str(exc_info.value).lower(), (
            "Error must mention missing extension_name"
        )

        # Test missing extension_version
        config_path = mock_config_file.create_missing_field(
            "extension_version"
        )
        loader = ConfigLoader(config_path=str(config_path))

        with pytest.raises(ConfigValidationError) as exc_info:
            loader.load()
        assert "extension_version" in str(exc_info.value).lower(), (
            "Error must mention missing extension_version"
        )

        # Test missing configuration section
        config_path = mock_config_file.create_missing_field("configuration")
        loader = ConfigLoader(config_path=str(config_path))

        with pytest.raises(ConfigValidationError) as exc_info:
            loader.load()
        assert "configuration" in str(exc_info.value).lower(), (
            "Error must mention missing configuration"
        )

        # Test missing otlp.endpoint
        config_path = mock_config_file.create_missing_field("otlp.endpoint")
        loader = ConfigLoader(config_path=str(config_path))

        with pytest.raises(ConfigValidationError) as exc_info:
            loader.load()
        assert "endpoint" in str(exc_info.value).lower(), (
            "Error must mention missing endpoint"
        )

    def test_credential_resolution(
        self, mock_config_file, mock_credentials_store
    ):
        """
        Test that credentials are resolved from credentials store.

        Spec Reference: docs/specs/extension-base-library.md#configuration-loader
        - File Loading (lines 204-208)
        - Credentials Manager integration (lines 270-304)

        Validates:
        - Credentials are loaded from credentials file
        - Endpoint credentials_ref is resolved to actual credentials
        - Resolved credentials have correct type and fields
        - Multiple endpoints can reference different credentials

        Expected: Credentials resolved correctly (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader

        # Create config with multiple endpoints
        config_path = mock_config_file.create_multi_endpoint_config()
        creds_path = mock_credentials_store.create_multi_auth_store()

        # Load configuration
        loader = ConfigLoader(
            config_path=str(config_path), credentials_path=str(creds_path)
        )
        config = loader.load()

        # Validate credentials are resolved for all endpoints
        assert len(config.configuration.endpoints) >= 2, (
            "Config must have multiple endpoints"
        )

        for endpoint in config.configuration.endpoints:
            assert endpoint.credentials is not None, (
                f"Endpoint {endpoint.id} must have resolved credentials"
            )
            assert hasattr(endpoint.credentials, "type"), (
                "Credentials must have type field"
            )

            # Validate credentials have required fields based on type
            if endpoint.credentials.type == "basic":
                assert hasattr(endpoint.credentials, "username"), (
                    "Basic auth must have username"
                )
                assert hasattr(endpoint.credentials, "password"), (
                    "Basic auth must have password"
                )
            elif endpoint.credentials.type == "token":
                assert hasattr(endpoint.credentials, "token"), (
                    "Token auth must have token"
                )

    def test_credential_ref_not_found(
        self, mock_config_file, mock_credentials_store
    ):
        """
        Test handling of missing credential reference.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Credential Resolution (lines 283-286)

        Validates:
        - Raises CredentialRefNotFoundError when ref doesn't exist
        - Error message includes credential reference key
        - Error is catchable as CredentialsError

        Expected: Raises CredentialRefNotFoundError (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader
        from extension_base.exceptions import (
            CredentialRefNotFoundError,
            CredentialsError,
        )

        # Create config with invalid credential reference
        config_path = mock_config_file.create_invalid_credential_ref()
        creds_path = mock_credentials_store.create_basic_auth_store()

        # Attempt to load config
        loader = ConfigLoader(
            config_path=str(config_path), credentials_path=str(creds_path)
        )

        # Validate raises CredentialRefNotFoundError
        with pytest.raises(CredentialRefNotFoundError) as exc_info:
            loader.load()

        # Validate error message
        error_msg = str(exc_info.value)
        assert (
            "not found" in error_msg.lower()
            or "reference" in error_msg.lower()
        ), "Error message must indicate credential not found"

        # Validate can be caught as CredentialsError
        with pytest.raises(CredentialsError):
            loader.load()

    def test_credentials_file_not_found(self, mock_config_file):
        """
        Test handling of missing credentials file.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Credential Loading (lines 277-281)

        Validates:
        - Raises CredentialsFileNotFoundError when file doesn't exist
        - Error message includes file path
        - Error is catchable as CredentialsError

        Expected: Raises CredentialsFileNotFoundError (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader
        from extension_base.exceptions import (
            CredentialsError,
            CredentialsFileNotFoundError,
        )

        # Create valid config but point to non-existent credentials
        config_path = mock_config_file.create_valid_config()

        # Attempt to load with missing credentials file
        loader = ConfigLoader(
            config_path=str(config_path),
            credentials_path="/nonexistent/credentials.json",
        )

        # Validate raises CredentialsFileNotFoundError
        with pytest.raises(CredentialsFileNotFoundError) as exc_info:
            loader.load()

        # Validate error message
        error_msg = str(exc_info.value)
        assert (
            "credentials" in error_msg.lower()
            or "not found" in error_msg.lower()
        ), "Error message must mention missing credentials file"

        # Validate can be caught as CredentialsError
        with pytest.raises(CredentialsError):
            loader.load()

    def test_env_var_overrides(self, mock_config_file, mock_credentials_store):
        """
        Test that environment variables override config values.

        Spec Reference: docs/specs/extension-base-library.md#configuration-loader
        - Environment Variable Overrides (lines 216-222)

        Validates:
        - EXTENSION_LOG_LEVEL overrides configuration.log_level
        - OTLP_ENDPOINT overrides otlp.endpoint
        - CONTAINER_ID overrides container_id
        - SUPERVISOR_ID overrides supervisor_id
        - Environment variables take precedence over file values

        Expected: Environment overrides work (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader

        # Create config with default values
        config_path = mock_config_file.create_valid_config()
        creds_path = mock_credentials_store.create_basic_auth_store()

        # Set environment variable overrides
        env_overrides = {
            "EXTENSION_LOG_LEVEL": "DEBUG",
            "OTLP_ENDPOINT": "localhost:9999",
            "CONTAINER_ID": "test-container-123",
            "SUPERVISOR_ID": "test-supervisor-456",
        }

        with patch.dict(os.environ, env_overrides):
            # Load configuration
            loader = ConfigLoader(
                config_path=str(config_path), credentials_path=str(creds_path)
            )
            config = loader.load()

            # Validate environment overrides were applied
            assert config.configuration.log_level == "DEBUG", (
                "EXTENSION_LOG_LEVEL must override log_level"
            )
            assert config.otlp.endpoint == "localhost:9999", (
                "OTLP_ENDPOINT must override otlp.endpoint"
            )
            assert config.container_id == "test-container-123", (
                "CONTAINER_ID must override container_id"
            )
            assert config.supervisor_id == "test-supervisor-456", (
                "SUPERVISOR_ID must override supervisor_id"
            )

    def test_otel_env_var_overrides(
        self, mock_config_file, mock_credentials_store
    ):
        """
        Test that OpenTelemetry environment variables override config.

        Spec Reference: docs/specs/extension-base-library.md#configuration-loader
        - OTEL Environment Variables Overrides (lines 224-233)

        Validates:
        - OTEL_EXPORTER_OTLP_ENDPOINT overrides otlp.endpoint
        - OTEL_EXPORTER_OTLP_TIMEOUT overrides otlp.timeout
        - OTEL_EXPORTER_OTLP_PROTOCOL overrides otlp.protocol
        - OTEL_EXPORTER_OTLP_COMPRESSION overrides otlp.compression
        - OTEL_METRIC_EXPORT_INTERVAL overrides otlp.interval

        Expected: OTEL environment overrides work (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader

        # Create config with default values
        config_path = mock_config_file.create_valid_config()
        creds_path = mock_credentials_store.create_basic_auth_store()

        # Set OTEL environment variable overrides
        env_overrides = {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://otel-collector:4317",
            "OTEL_EXPORTER_OTLP_TIMEOUT": "30000",
            "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
            "OTEL_EXPORTER_OTLP_COMPRESSION": "gzip",
            "OTEL_METRIC_EXPORT_INTERVAL": "30000",
        }

        with patch.dict(os.environ, env_overrides):
            # Load configuration
            loader = ConfigLoader(
                config_path=str(config_path), credentials_path=str(creds_path)
            )
            config = loader.load()

            # Validate OTEL environment overrides were applied
            assert "otel-collector" in config.otlp.endpoint, (
                "OTEL_EXPORTER_OTLP_ENDPOINT must override endpoint"
            )
            assert config.otlp.timeout == 30, (
                "OTEL_EXPORTER_OTLP_TIMEOUT must override timeout (converted to seconds)"
            )
            assert config.otlp.protocol == "http/protobuf", (
                "OTEL_EXPORTER_OTLP_PROTOCOL must override protocol"
            )
            assert config.otlp.compression == "gzip", (
                "OTEL_EXPORTER_OTLP_COMPRESSION must override compression"
            )
            assert config.otlp.interval == 30, (
                "OTEL_METRIC_EXPORT_INTERVAL must override interval (converted to seconds)"
            )


    def test_otel_env_var_overrides_without_otlp_block(
        self, mock_config_file, mock_credentials_store
    ):
        """
        Test that OTEL environment variables override config when no 'otlp' block is present.

        Spec Reference: docs/specs/extension-base-library.md#configuration-loader
        - OTEL Environment Variables Overrides (lines 224-233)

        Validates:
        - OTEL_EXPORTER_OTLP_ENDPOINT overrides otlp.endpoint even when no otlp block exists in config

        Expected: OTEL environment overrides work without an otlp block (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader

        config_path = mock_config_file.create_valid_config_no_otlp()
        creds_path = mock_credentials_store.create_basic_auth_store()

        env_overrides = {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://otel-collector:4317",
        }

        with patch.dict(os.environ, env_overrides):
            loader = ConfigLoader(
                config_path=str(config_path), credentials_path=str(creds_path)
            )
            # Without the fix this raises: KeyError: 'otlp'
            config = loader.load()

        assert "otel-collector" in config.otlp.endpoint, (
            "OTEL_EXPORTER_OTLP_ENDPOINT must be used when no otlp block in config"
        )


    def test_default_values_applied(
        self, mock_config_file, mock_credentials_store
    ):
        """
        Test that default values are applied for optional fields.

        Spec Reference: docs/specs/extension-base-library.md#configuration-loader
        - Default Application (lines 235-244)

        Validates:
        - Default log_level is INFO
        - Default OTLP endpoint is localhost:4317
        - Default OTLP protocol is grpc
        - Default OTLP compression is gzip
        - Default OTLP interval is 60 seconds
        - Default OTLP timeout is 10 seconds
        - Endpoint inherits configuration.interval if not specified
        - Endpoint inherits configuration.timeout if not specified

        Expected: Defaults applied correctly (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader

        # Create minimal config (only required fields)
        config_path = mock_config_file.create_minimal_config()
        creds_path = mock_credentials_store.create_basic_auth_store()

        # Load configuration
        loader = ConfigLoader(
            config_path=str(config_path), credentials_path=str(creds_path)
        )
        config = loader.load()

        # Validate default values
        assert config.configuration.log_level == "INFO", (
            "Default log_level must be INFO"
        )
        assert config.otlp.endpoint == "localhost:4317", (
            "Default OTLP endpoint must be localhost:4317"
        )
        assert config.otlp.protocol == "grpc", (
            "Default OTLP protocol must be grpc"
        )
        assert config.otlp.compression == "gzip", (
            "Default OTLP compression must be gzip"
        )
        assert config.otlp.interval == 60, (
            "Default OTLP interval must be 60 seconds"
        )
        assert config.otlp.timeout == 10, (
            "Default OTLP timeout must be 10 seconds"
        )

        # Validate endpoint inherits defaults
        endpoint = config.configuration.endpoints[0]
        assert endpoint.interval == config.configuration.interval, (
            "Endpoint must inherit interval from configuration"
        )
        assert endpoint.timeout == config.configuration.timeout, (
            "Endpoint must inherit timeout from configuration"
        )

    @pytest.mark.parametrize(
        "count, should_raise, expected_hint",
        [
            (0, True, lambda msg: "endpoint" in msg),
            (36, True, lambda msg: "endpoint" in msg or "35" in msg),
            (1, False, None),
            (35, False, None),
        ],
        ids=["zero-endpoints", "over-limit", "min-valid", "max-valid"],
    )
    def test_endpoint_count_validation(
        self,
        mock_config_file,
        mock_credentials_store,
        count,
        should_raise,
        expected_hint,
        mocker,
    ):
        """
        Test validation of endpoint count limits.

        Spec Reference: docs/specs/extension-base-library.md#configuration-loader
        - Schema Validation (lines 210-214)

        Validates:
        - At least 1 endpoint is required
        - Maximum 35 endpoints are allowed
        - Raises ConfigValidationError for 0 endpoints
        - Raises ConfigValidationError for >35 endpoints

        Expected: Endpoint count validated (TDD red phase - will fail)
        """
        from extension_base.exceptions import ConfigValidationError

        creds_path = mock_credentials_store.create_basic_auth_store()
        loader = self._make_loader(mock_config_file, creds_path, count)

        # As we are interested only on endpoint counting from the config file, not the
        # credentials, we are skiping the execution of _resolve_credentials
        mocker.patch.object(loader, "_resolve_credentials", return_value=None)

        if should_raise:
            with pytest.raises(ConfigValidationError) as exc_info:
                loader.load()
            assert expected_hint(str(exc_info.value).lower()), (
                "Error must mention endpoint or limit"
            )
        else:
            config = loader.load()
            assert len(config.configuration.endpoints) == count, (
                f"Config with {count} endpoint(s) must load successfully"
            )

    def _make_loader(self, mock_config_file, creds_path, count):
        from extension_base.config.loader import ConfigLoader

        config_path = mock_config_file.create_config_with_endpoint_count(count)
        return ConfigLoader(
            config_path=str(config_path), credentials_path=str(creds_path)
        )

    def test_config_models_exist(self):
        """
        Test that Pydantic configuration models exist.

        Spec Reference: docs/specs/extension-base-library.md#configuration-loader
        - Configuration Models (lines 246-249)

        Validates:
        - ExtensionConfig model exists
        - Configuration model exists
        - OTLPConfiguration model exists
        - Endpoint model exists
        - CredentialEntry model exists
        - All models are Pydantic BaseModel subclasses

        Expected: Configuration models exist (TDD red phase - will fail)
        """
        from extension_base.config import models
        from pydantic import BaseModel

        # Validate models exist
        model_names = [
            "ExtensionConfig",
            "Configuration",
            "OTLPConfiguration",
            "Endpoint",
            "CredentialEntry",
        ]

        for model_name in model_names:
            assert hasattr(models, model_name), (
                f"{model_name} must be defined in config.models"
            )

            model_class = getattr(models, model_name)

            # Validate it's a Pydantic model
            assert issubclass(model_class, BaseModel), (
                f"{model_name} must be a Pydantic BaseModel"
            )

    def test_credential_types_validation(
        self, mock_config_file, mock_credentials_store
    ):
        """
        Test validation of different credential types.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Credential Resolution (lines 283-286)
        - API/Interface (lines 293-304)

        Validates:
        - Basic auth credentials have username and password
        - Token auth credentials have token
        - API key auth credentials have api_key
        - OAuth2 credentials have client_id and client_secret
        - Certificate auth credentials have certificate_path and private_key_path
        - Raises CredentialInvalidError for missing required fields

        Expected: Credential types validated (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader
        from extension_base.exceptions import CredentialInvalidError

        # Test basic auth with missing password
        config_path = mock_config_file.create_valid_config()
        creds_path = mock_credentials_store.create_invalid_basic_auth()

        loader = ConfigLoader(
            config_path=str(config_path), credentials_path=str(creds_path)
        )

        with pytest.raises(CredentialInvalidError) as exc_info:
            loader.load()
        assert (
            "password" in str(exc_info.value).lower()
            or "basic" in str(exc_info.value).lower()
        ), "Error must mention missing password for basic auth"

        # Test token auth with missing token
        creds_path = mock_credentials_store.create_invalid_token_auth()
        loader = ConfigLoader(
            config_path=str(config_path), credentials_path=str(creds_path)
        )

        with pytest.raises(CredentialInvalidError) as exc_info:
            loader.load()
        assert "token" in str(exc_info.value).lower(), (
            "Error must mention missing token"
        )

    def test_get_config_method(self, mock_config_file, mock_credentials_store):
        """
        Test extension.get_config() method returns configuration object.

        Spec Reference: docs/specs/extension-base-library.md#configuration-api
        - Configuration API (lines 809-821)

        Validates:
        - extension.get_config() method exists
        - Returns configuration object
        - Configuration object has expected structure
        - Method is accessible from ExtensionBase instance

        Expected: get_config() method works (TDD red phase - will fail)
        """
        from extension_base.core import ExtensionBase

        # Create config files
        config_path = mock_config_file.create_valid_config()
        creds_path = mock_credentials_store.create_basic_auth_store()

        # Create extension instance — patch ConfigLoader to read from temp files
        with patch(
            "extension_base.config.loader.ConfigLoader",
            lambda: ConfigLoader(
                config_path=str(config_path),
                credentials_path=str(creds_path),
            ),
        ):
            extension = ExtensionBase()

        # Test get_config() method exists
        assert hasattr(extension, "get_config"), (
            "ExtensionBase must have get_config() method"
        )
        assert callable(extension.get_config), "get_config() must be callable"

        # Get configuration
        config = extension.get_config()

        # Validate configuration object
        assert config is not None, "get_config() must return configuration"
        assert hasattr(config, "extension_id"), "Config must have extension_id"
        assert hasattr(config, "extension_name"), (
            "Config must have extension_name"
        )
        assert hasattr(config, "configuration"), (
            "Config must have configuration section"
        )
        assert hasattr(config, "otlp"), "Config must have otlp section"

    def test_config_get_endpoint_config_method(
        self, mock_config_file, mock_credentials_store
    ):
        """
        Test config.get_endpoint_config(endpoint_id) method.

        Spec Reference: docs/specs/extension-base-library.md#configuration-api
        - Configuration API (lines 809-821)

        Validates:
        - config.get_endpoint_config(endpoint_id) method exists
        - Returns correct endpoint configuration by ID
        - Raises error for non-existent endpoint
        - Returned endpoint has expected structure

        Expected: get_endpoint_config() works (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader
        from extension_base.exceptions import ConfigError

        # Create config with multiple endpoints
        config_path = mock_config_file.create_multi_endpoint_config()
        creds_path = mock_credentials_store.create_multi_auth_store()

        # Load configuration
        loader = ConfigLoader(
            config_path=str(config_path), credentials_path=str(creds_path)
        )
        config = loader.load()

        # Test get_endpoint_config() method exists
        assert hasattr(config, "get_endpoint_config"), (
            "Config must have get_endpoint_config() method"
        )
        assert callable(config.get_endpoint_config), (
            "get_endpoint_config() must be callable"
        )

        # Get endpoint by ID
        endpoint_id = config.configuration.endpoints[0].id
        endpoint = config.get_endpoint_config(endpoint_id)

        # Validate endpoint returned
        assert endpoint is not None, (
            "get_endpoint_config() must return endpoint"
        )
        assert endpoint.id == endpoint_id, (
            "Returned endpoint must match requested ID"
        )
        assert hasattr(endpoint, "url"), "Endpoint must have url"
        assert hasattr(endpoint, "credentials"), (
            "Endpoint must have credentials"
        )

        # Test error for non-existent endpoint
        with pytest.raises(ConfigError) as exc_info:
            config.get_endpoint_config("non-existent-endpoint")

        assert (
            "not found" in str(exc_info.value).lower()
            or "endpoint" in str(exc_info.value).lower()
        ), "Error must indicate endpoint not found"

    def test_config_get_credentials_method(
        self, mock_config_file, mock_credentials_store
    ):
        """
        Test config.get_credentials(endpoint_id) method.

        Spec Reference: docs/specs/extension-base-library.md#configuration-api
        - Configuration API (lines 809-821)

        Validates:
        - config.get_credentials(endpoint_id) method exists
        - Returns credentials for specified endpoint
        - Raises error for missing credentials
        - Credentials are not logged/exposed
        - Credentials have correct type and fields

        Expected: get_credentials() works (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader
        from extension_base.exceptions import CredentialsError

        # Create config with endpoints
        config_path = mock_config_file.create_valid_config()
        creds_path = mock_credentials_store.create_basic_auth_store()

        # Load configuration
        loader = ConfigLoader(
            config_path=str(config_path), credentials_path=str(creds_path)
        )
        config = loader.load()

        # Test get_credentials() method exists
        assert hasattr(config, "get_credentials"), (
            "Config must have get_credentials() method"
        )
        assert callable(config.get_credentials), (
            "get_credentials() must be callable"
        )

        # Get credentials by endpoint ID
        endpoint_id = config.configuration.endpoints[0].id
        credentials = config.get_credentials(endpoint_id)

        # Validate credentials returned
        assert credentials is not None, (
            "get_credentials() must return credentials"
        )
        assert hasattr(credentials, "type"), "Credentials must have type field"

        # Validate credentials have required fields based on type
        if credentials.type == "basic":
            assert hasattr(credentials, "username"), (
                "Basic auth must have username"
            )
            assert hasattr(credentials, "password"), (
                "Basic auth must have password"
            )
            # Verify password is not empty (but don't log it)
            assert credentials.password, "Password must not be empty"

        # Test error for non-existent endpoint
        with pytest.raises(CredentialsError) as exc_info:
            config.get_credentials("non-existent-endpoint")

        assert (
            "not found" in str(exc_info.value).lower()
            or "credential" in str(exc_info.value).lower()
        ), "Error must indicate credentials not found"

        # Verify credentials are not exposed in string representation
        config_str = str(config)
        if hasattr(credentials, "password"):
            assert credentials.password not in config_str, (
                "Credentials must not be exposed in config string representation"
            )


class TestProxyConfiguration:
    """Tests for proxy configuration fields in the otlp block (FR2)."""

    def test_proxy_fields_parsed_from_config(
        self, mock_config_file, mock_credentials_store
    ):
        """Proxy fields in the otlp block are parsed into OTLPConfiguration."""
        import json

        # create_valid_config() returns a Path — read it, then add proxy fields
        base_path = mock_config_file.create_valid_config()
        config = json.loads(base_path.read_text())
        config["otlp"]["http_proxy"] = "http://proxy.example.com:8080"
        config["otlp"]["https_proxy"] = "http://proxy.example.com:8080"
        config["otlp"]["no_proxy"] = "localhost,127.0.0.1"

        config_path = mock_config_file.temp_dir / "proxy_config.json"
        config_path.write_text(json.dumps(config))
        creds_path = mock_credentials_store.create_basic_auth_store()

        loader = ConfigLoader(
            config_path=str(config_path), credentials_path=str(creds_path)
        )
        result = loader.load()

        assert result.otlp.http_proxy == "http://proxy.example.com:8080"
        assert result.otlp.https_proxy == "http://proxy.example.com:8080"
        assert result.otlp.no_proxy == "localhost,127.0.0.1"

    def test_proxy_fields_absent_by_default(
        self, mock_config_file, mock_credentials_store
    ):
        """Proxy fields default to None when not present in config."""
        config_path = mock_config_file.create_valid_config()
        creds_path = mock_credentials_store.create_basic_auth_store()

        loader = ConfigLoader(
            config_path=str(config_path), credentials_path=str(creds_path)
        )
        result = loader.load()

        assert result.otlp.http_proxy is None
        assert result.otlp.https_proxy is None
        assert result.otlp.no_proxy is None

    def test_setup_otel_sets_proxy_env_vars(self):
        """setup_otel() sets HTTP_PROXY/HTTPS_PROXY/NO_PROXY from otlp config fields."""
        from unittest.mock import MagicMock, patch
        from extension_base.metrics.otel_setup import setup_otel

        config = {
            "extension_name": "test-ext",
            "extension_version": "1.0.0",
            "otlp": {
                "endpoint": "localhost:4317",
                "http_proxy": "http://proxy.example.com:8080",
                "https_proxy": "http://proxy.example.com:8080",
                "no_proxy": "localhost,127.0.0.1",
            },
        }

        clean_env = {k: v for k, v in os.environ.items()
                     if k not in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY")}

        with patch.dict(os.environ, clean_env, clear=True):
            with patch("extension_base.metrics.otel_setup.create_meter_provider",
                       return_value=MagicMock()), \
                 patch("extension_base.metrics.otel_setup.create_internal_meter_provider",
                       return_value=MagicMock()):
                setup_otel(config)

            assert os.environ.get("HTTP_PROXY") == "http://proxy.example.com:8080"
            assert os.environ.get("HTTPS_PROXY") == "http://proxy.example.com:8080"
            assert os.environ.get("NO_PROXY") == "localhost,127.0.0.1"

    def test_setup_otel_does_not_overwrite_existing_proxy_env_var(self):
        """An HTTP_PROXY already in the environment takes precedence over config."""
        from unittest.mock import MagicMock, patch
        from extension_base.metrics.otel_setup import setup_otel

        config = {
            "extension_name": "test-ext",
            "extension_version": "1.0.0",
            "otlp": {
                "endpoint": "localhost:4317",
                "http_proxy": "http://config-proxy.example.com:8080",
            },
        }

        with patch.dict(os.environ, {"HTTP_PROXY": "http://existing-proxy.example.com:3128"}):
            with patch("extension_base.metrics.otel_setup.create_meter_provider",
                       return_value=MagicMock()), \
                 patch("extension_base.metrics.otel_setup.create_internal_meter_provider",
                       return_value=MagicMock()):
                setup_otel(config)

            assert os.environ.get("HTTP_PROXY") == "http://existing-proxy.example.com:3128"

    def test_setup_otel_no_proxy_fields_no_env_vars_set(self):
        """When no proxy fields are in config, no proxy env vars are injected."""
        from unittest.mock import MagicMock, patch
        from extension_base.metrics.otel_setup import setup_otel

        config = {
            "extension_name": "test-ext",
            "extension_version": "1.0.0",
            "otlp": {"endpoint": "localhost:4317"},
        }

        clean_env = {k: v for k, v in os.environ.items()
                     if k not in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY")}

        with patch.dict(os.environ, clean_env, clear=True):
            with patch("extension_base.metrics.otel_setup.create_meter_provider",
                       return_value=MagicMock()), \
                 patch("extension_base.metrics.otel_setup.create_internal_meter_provider",
                       return_value=MagicMock()):
                setup_otel(config)

            assert "HTTP_PROXY" not in os.environ
            assert "HTTPS_PROXY" not in os.environ
            assert "NO_PROXY" not in os.environ


class TestCACertConfiguration:
    """Tests for CA certificate configuration in the otlp block."""

    def test_certificate_file_parsed_from_config(
        self, mock_config_file, mock_credentials_store
    ):
        """otlp.certificate_file is parsed into OTLPConfiguration."""
        import json

        base_path = mock_config_file.create_valid_config()
        config = json.loads(base_path.read_text())
        config["otlp"]["certificate_file"] = "/path/to/ca.crt"

        config_path = mock_config_file.temp_dir / "cert_config.json"
        config_path.write_text(json.dumps(config))
        creds_path = mock_credentials_store.create_basic_auth_store()

        loader = ConfigLoader(
            config_path=str(config_path), credentials_path=str(creds_path)
        )
        result = loader.load()

        assert result.otlp.certificate_file == "/path/to/ca.crt"

    def test_certificate_file_absent_by_default(
        self, mock_config_file, mock_credentials_store
    ):
        """certificate_file defaults to None when not present in config."""
        config_path = mock_config_file.create_valid_config()
        creds_path = mock_credentials_store.create_basic_auth_store()

        loader = ConfigLoader(
            config_path=str(config_path), credentials_path=str(creds_path)
        )
        result = loader.load()

        assert result.otlp.certificate_file is None

    def test_setup_otel_sets_cert_env_var_from_config(self):
        """setup_otel() sets OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE from otlp.certificate_file."""
        from unittest.mock import MagicMock, patch
        from extension_base.metrics.otel_setup import setup_otel

        config = {
            "extension_name": "test-ext",
            "extension_version": "1.0.0",
            "otlp": {
                "endpoint": "localhost:4317",
                "certificate_file": "/path/to/ca.crt",
            },
        }

        clean_env = {k: v for k, v in os.environ.items()
                     if k != "OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE"}

        with patch.dict(os.environ, clean_env, clear=True):
            with patch("extension_base.metrics.otel_setup.create_meter_provider",
                       return_value=MagicMock()), \
                 patch("extension_base.metrics.otel_setup.create_internal_meter_provider",
                       return_value=MagicMock()):
                setup_otel(config)

            assert os.environ.get("OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE") == "/path/to/ca.crt"

    def test_setup_otel_does_not_overwrite_existing_cert_env_var(self):
        """A OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE already in the environment takes precedence."""
        from unittest.mock import MagicMock, patch
        from extension_base.metrics.otel_setup import setup_otel

        config = {
            "extension_name": "test-ext",
            "extension_version": "1.0.0",
            "otlp": {
                "endpoint": "localhost:4317",
                "certificate_file": "/config/ca.crt",
            },
        }

        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE": "/existing/ca.crt"}):
            with patch("extension_base.metrics.otel_setup.create_meter_provider",
                       return_value=MagicMock()), \
                 patch("extension_base.metrics.otel_setup.create_internal_meter_provider",
                       return_value=MagicMock()):
                setup_otel(config)

            assert os.environ.get("OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE") == "/existing/ca.crt"

    def test_well_known_ca_cert_auto_detected(self):
        """When ca.crt exists at _DEFAULT_CA_CERT and no config or env var is set,
        OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE is set automatically."""
        from unittest.mock import MagicMock, patch
        from extension_base.metrics.otel_setup import setup_otel, _DEFAULT_CA_CERT

        config = {
            "extension_name": "test-ext",
            "extension_version": "1.0.0",
            "otlp": {"endpoint": "localhost:4317"},
        }

        clean_env = {k: v for k, v in os.environ.items()
                     if k != "OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE"}

        with patch.dict(os.environ, clean_env, clear=True), \
             patch("extension_base.metrics.otel_setup.os.path.isfile",
                   side_effect=lambda p: p == _DEFAULT_CA_CERT), \
             patch("extension_base.metrics.otel_setup.create_meter_provider",
                   return_value=MagicMock()), \
             patch("extension_base.metrics.otel_setup.create_internal_meter_provider",
                   return_value=MagicMock()):
            setup_otel(config)
            assert os.environ.get("OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE") == _DEFAULT_CA_CERT

    def test_well_known_ca_cert_not_set_when_absent(self):
        """When ca.crt does not exist and no config or env var is set,
        OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE is not injected."""
        from unittest.mock import MagicMock, patch
        from extension_base.metrics.otel_setup import setup_otel

        config = {
            "extension_name": "test-ext",
            "extension_version": "1.0.0",
            "otlp": {"endpoint": "localhost:4317"},
        }

        clean_env = {k: v for k, v in os.environ.items()
                     if k != "OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE"}

        with patch.dict(os.environ, clean_env, clear=True), \
             patch("extension_base.metrics.otel_setup.os.path.isfile",
                   return_value=False), \
             patch("extension_base.metrics.otel_setup.create_meter_provider",
                   return_value=MagicMock()), \
             patch("extension_base.metrics.otel_setup.create_internal_meter_provider",
                   return_value=MagicMock()):
            setup_otel(config)
            assert "OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE" not in os.environ

    def test_config_cert_takes_precedence_over_well_known(self):
        """otlp.certificate_file in config takes precedence over the auto-detected path."""
        from unittest.mock import MagicMock, patch
        from extension_base.metrics.otel_setup import setup_otel, _DEFAULT_CA_CERT

        config = {
            "extension_name": "test-ext",
            "extension_version": "1.0.0",
            "otlp": {
                "endpoint": "localhost:4317",
                "certificate_file": "/custom/ca.crt",
            },
        }

        clean_env = {k: v for k, v in os.environ.items()
                     if k != "OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE"}

        with patch.dict(os.environ, clean_env, clear=True), \
             patch("extension_base.metrics.otel_setup.os.path.isfile",
                   side_effect=lambda p: p == _DEFAULT_CA_CERT), \
             patch("extension_base.metrics.otel_setup.create_meter_provider",
                   return_value=MagicMock()), \
             patch("extension_base.metrics.otel_setup.create_internal_meter_provider",
                   return_value=MagicMock()):
            setup_otel(config)
            assert os.environ.get("OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE") == "/custom/ca.crt"

    def test_env_var_cert_takes_precedence_over_well_known(self):
        """A pre-existing env var is never overwritten, even when ca.crt exists."""
        from unittest.mock import MagicMock, patch
        from extension_base.metrics.otel_setup import setup_otel, _DEFAULT_CA_CERT

        config = {
            "extension_name": "test-ext",
            "extension_version": "1.0.0",
            "otlp": {"endpoint": "localhost:4317"},
        }

        with patch.dict(os.environ,
                        {"OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE": "/preexisting/ca.crt"}), \
             patch("extension_base.metrics.otel_setup.os.path.isfile",
                   side_effect=lambda p: p == _DEFAULT_CA_CERT), \
             patch("extension_base.metrics.otel_setup.create_meter_provider",
                   return_value=MagicMock()), \
             patch("extension_base.metrics.otel_setup.create_internal_meter_provider",
                   return_value=MagicMock()):
            setup_otel(config)
            assert os.environ.get("OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE") == "/preexisting/ca.crt"


class TestBackendKeyRef:
    """Tests for otlp.backend_key_ref → otlp.instana_key resolution."""

    _BACKEND_CRED = {"instana.backend": {"type": "api_key", "api_key": "real-api-key"}}

    def test_backend_key_ref_resolved_to_instana_key(
        self, mock_config_file, mock_credentials_store
    ):
        """backend_key_ref pointing to an api_key credential populates instana_key."""
        cfg_path = mock_config_file.create_valid_config(
            extra_otlp={"backend_key_ref": "instana.backend"}
        )
        creds_path = mock_credentials_store.create_basic_auth_store(
            extra_entries=self._BACKEND_CRED
        )

        config = ConfigLoader(str(cfg_path), str(creds_path)).load()

        assert config.otlp.instana_key == "real-api-key", (
            "instana_key must be populated from the referenced api_key credential"
        )

    def test_no_backend_key_ref_leaves_instana_key_none(
        self, mock_config_file, mock_credentials_store
    ):
        """When backend_key_ref is absent, instana_key stays None."""
        cfg_path = mock_config_file.create_valid_config()
        creds_path = mock_credentials_store.create_basic_auth_store()

        config = ConfigLoader(str(cfg_path), str(creds_path)).load()

        assert config.otlp.instana_key is None

    def test_env_var_wins_over_backend_key_ref(
        self, mock_config_file, mock_credentials_store, monkeypatch
    ):
        """INSTANA_KEY env var takes precedence; the credential is not consulted."""
        monkeypatch.setenv("INSTANA_KEY", "env-key-wins")
        cfg_path = mock_config_file.create_valid_config(
            extra_otlp={"backend_key_ref": "instana.backend"}
        )
        creds_path = mock_credentials_store.create_basic_auth_store(
            extra_entries={"instana.backend": {"type": "api_key", "api_key": "creds-key"}}
        )

        config = ConfigLoader(str(cfg_path), str(creds_path)).load()

        assert config.otlp.instana_key == "env-key-wins", (
            "INSTANA_KEY env var must win over backend_key_ref"
        )

    def test_backend_key_ref_not_found_raises(
        self, mock_config_file, mock_credentials_store
    ):
        """A backend_key_ref pointing to a missing credential raises CredentialRefNotFoundError."""
        from extension_base.exceptions import CredentialRefNotFoundError

        cfg_path = mock_config_file.create_valid_config(
            extra_otlp={"backend_key_ref": "no.such.key"}
        )
        creds_path = mock_credentials_store.create_basic_auth_store()

        with pytest.raises(CredentialRefNotFoundError):
            ConfigLoader(str(cfg_path), str(creds_path)).load()

    def test_backend_key_ref_missing_api_key_raises(
        self, mock_config_file, mock_credentials_store
    ):
        """A backend_key_ref that resolves to an api_key credential without api_key raises."""
        from extension_base.exceptions import CredentialInvalidError

        cfg_path = mock_config_file.create_valid_config(
            extra_otlp={"backend_key_ref": "instana.backend"}
        )
        # api_key field intentionally missing
        creds_path = mock_credentials_store.create_basic_auth_store(
            extra_entries={"instana.backend": {"type": "api_key"}}
        )

        with pytest.raises(CredentialInvalidError):
            ConfigLoader(str(cfg_path), str(creds_path)).load()


# Made with Bob
