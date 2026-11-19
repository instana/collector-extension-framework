# (c) Copyright IBM Corp. 2026
"""
Mock objects for Extension Base Library testing.

This module provides mock implementations of external dependencies
for isolated unit testing:

- MockOTLPServer: Simulated OTLP endpoint for metrics export testing
- MockConfigFile: Temporary configuration files with various scenarios
- MockCredentialsStore: Temporary credentials files for auth testing

Usage:
    from tests.mocks import MockOTLPServer, MockConfigFile, MockCredentialsStore

    # Create mock OTLP server
    server = MockOTLPServer()
    server.start()

    # Create mock config file
    config_gen = MockConfigFile()
    config_path = config_gen.create_valid_config()

    # Create mock credentials
    creds_gen = MockCredentialsStore()
    creds_path = creds_gen.create_basic_auth_store()
"""

from tests.mocks.mock_config import (
    MockConfigFile,
    create_valid_config,
)
from tests.mocks.mock_credentials import (
    MockCredentialsStore,
    create_basic_auth_credentials,
)
from tests.mocks.mock_otlp import (
    MockOTLPServer,
    create_mock_meter_provider,
)

__all__ = [
    # OTLP mocks
    "MockOTLPServer",
    "create_mock_meter_provider",
    # Config mocks
    "MockConfigFile",
    "create_valid_config",
    # Credentials mocks
    "MockCredentialsStore",
    "create_basic_auth_credentials",
]

# Made with Bob
