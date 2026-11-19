# (c) Copyright IBM Corp. 2026
"""
Shared pytest fixtures for Extension Base Library tests.

This module provides reusable fixtures for all test modules:
- Mock OTLP servers
- Temporary configuration files
- Temporary credentials files
- Mock OpenTelemetry components
- Test environment setup/teardown
"""

import json
from unittest.mock import patch

import pytest

from tests.mocks import (
    MockConfigFile,
    MockCredentialsStore,
    MockOTLPServer,
    create_basic_auth_credentials,
    create_mock_meter_provider,
    create_valid_config,
)

# ============================================================================
# Prevent real OTLP network calls during tests
# ============================================================================
#
# Any test that calls setup_otel() or create_meter_provider() creates a
# PeriodicExportingMetricReader that retries against a live endpoint in a
# background thread, causing the test suite to hang.
# This autouse fixture replaces it with InMemoryMetricReader for every test.


@pytest.fixture(autouse=True)
def _patch_periodic_reader():
    """Replace PeriodicExportingMetricReader with InMemoryMetricReader.

    Applied to every test automatically to prevent background threads from
    making real OTLP network calls and hanging the test suite.
    """
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader

    def _in_memory_reader(*args, **kwargs):
        return InMemoryMetricReader()

    with patch(
        "extension_base.metrics.otel_setup.PeriodicExportingMetricReader",
        side_effect=_in_memory_reader,
    ):
        yield


# ============================================================================
# OTLP Server Fixtures
# ============================================================================


@pytest.fixture
def mock_otlp_server():
    """
    Provide a mock OTLP server for testing metrics export.

    Yields:
        MockOTLPServer: Started mock server

    Cleanup:
        Stops server after test
    """
    server = MockOTLPServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def mock_meter_provider():
    """
    Provide a mock MeterProvider.

    Returns:
        MagicMock: Mock MeterProvider with standard methods
    """
    return create_mock_meter_provider()


# ============================================================================
# Configuration File Fixtures
# ============================================================================


@pytest.fixture
def mock_config_file():
    """
    Provide a MockConfigFile generator for creating test configs.

    Yields:
        MockConfigFile: Config file generator

    Cleanup:
        Removes all created files after test
    """
    config_gen = MockConfigFile()
    yield config_gen
    config_gen.cleanup()


@pytest.fixture
def valid_config():
    """
    Provide a valid configuration dictionary.

    Returns:
        Dict: Valid configuration data
    """
    return create_valid_config()


# ============================================================================
# Credentials File Fixtures
# ============================================================================


@pytest.fixture
def mock_credentials_store():
    """
    Provide a MockCredentialsStore generator for creating test credentials.

    Yields:
        MockCredentialsStore: Credentials file generator

    Cleanup:
        Removes all created files after test
    """
    creds_gen = MockCredentialsStore()
    yield creds_gen
    creds_gen.cleanup()


@pytest.fixture
def valid_credentials():
    """
    Provide valid credentials as a JSON string.

    Returns:
        str: Valid credentials JSON string
    """
    return json.dumps(create_basic_auth_credentials())


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_endpoint_config():
    """
    Provide sample endpoint configuration as a SimpleNamespace.

    Returns a mutable object so tests can do ``sample_endpoint_config.tags = {...}``.
    """
    from types import SimpleNamespace
    ns = SimpleNamespace(
        id="test-ep-1",
        url="http://example.com:8080",
        credentials_ref="test-cred-1",
        interval=60,
        enabled=True,
        tags={"env": "test", "region": "us-east"},
        custom_params={"timeout": 30},
    )
    return ns


# Made with Bob
