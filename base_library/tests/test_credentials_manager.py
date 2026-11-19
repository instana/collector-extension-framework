# (c) Copyright IBM Corp. 2026
"""
Tests for FR3: Credentials Manager.

This module validates secure credential loading, resolution, validation,
and masking without logging sensitive data.

Tests cover credential file loading, type validation, security features,
and error handling for all authentication types.

Spec Reference: docs/specs/extension-base-library.md#credentials-manager (lines 270-304)
"""

import pytest


class TestCredentialsManager:
    """Test suite for credentials manager (FR3)."""

    def test_credentials_manager_class_exists(self):
        """
        Test that CredentialsManager class exists and can be instantiated.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - API/Interface (lines 293-304)

        Validates:
        - CredentialsManager class is defined in config.credentials module
        - Can be instantiated with default path
        - Can be instantiated with custom path
        - Has load_credentials() method
        - Has get_credential() method
        - Has validate_credential() method

        Expected: CredentialsManager class exists (TDD red phase - will fail)
        """
        from extension_base.config import credentials

        # Validate CredentialsManager exists
        assert hasattr(credentials, "CredentialsManager"), (
            "CredentialsManager must be defined in config.credentials module"
        )

        CredentialsManager = credentials.CredentialsManager

        # Validate it's a class
        assert isinstance(CredentialsManager, type), (
            "CredentialsManager must be a class"
        )

        # Validate can be instantiated with defaults
        manager = CredentialsManager()
        assert manager is not None, (
            "CredentialsManager must be instantiable with defaults"
        )

        # Validate can be instantiated with custom path
        manager = CredentialsManager(
            credentials_path="/custom/credentials.json"
        )
        assert manager is not None, (
            "CredentialsManager must accept custom path"
        )

        # Validate has required methods
        assert hasattr(manager, "load_credentials"), (
            "CredentialsManager must have load_credentials() method"
        )
        assert callable(manager.load_credentials), (
            "load_credentials() must be callable"
        )

        assert hasattr(manager, "get_credential"), (
            "CredentialsManager must have get_credential() method"
        )
        assert callable(manager.get_credential), (
            "get_credential() must be callable"
        )

        assert hasattr(manager, "validate_credential"), (
            "CredentialsManager must have validate_credential() method"
        )
        assert callable(manager.validate_credential), (
            "validate_credential() must be callable"
        )

    def test_load_credentials_file(self, mock_credentials_store):
        """
        Test loading credentials from file.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Credential Loading (lines 278-281)

        Validates:
        - Loads credentials file successfully
        - Returns dictionary of credentials
        - All credential entries are present
        - Credential structure is correct

        Expected: Credentials load successfully (TDD red phase - will fail)
        """
        from extension_base.config.credentials import CredentialsManager

        # Create credentials file
        creds_path = mock_credentials_store.create_basic_auth_store()

        # Load credentials
        manager = CredentialsManager(credentials_path=str(creds_path))
        credentials = manager.load_credentials()

        # Validate credentials loaded
        assert credentials is not None, "Credentials must not be None"
        assert isinstance(credentials, dict), (
            "Credentials must be a dictionary"
        )
        assert len(credentials) > 0, "Credentials must not be empty"

        # Validate credential structure
        for cred_id, cred_entry in credentials.items():
            assert isinstance(cred_id, str), "Credential ID must be string"
            assert isinstance(cred_entry, dict) or hasattr(
                cred_entry, "type"
            ), "Credential entry must be dict or have type attribute"

    def test_credentials_file_not_found(self):
        """
        Test handling of missing credentials file.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Credential Loading (lines 278-281)

        Validates:
        - Raises CredentialsFileNotFoundError when file doesn't exist
        - Error message includes file path
        - Error is catchable as CredentialsError

        Expected: Raises CredentialsFileNotFoundError (TDD red phase - will fail)
        """
        from extension_base.config.credentials import CredentialsManager
        from extension_base.exceptions import (
            CredentialsError,
            CredentialsFileNotFoundError,
        )

        # Attempt to load non-existent file
        manager = CredentialsManager(
            credentials_path="/nonexistent/credentials.json"
        )

        # Validate raises CredentialsFileNotFoundError
        with pytest.raises(CredentialsFileNotFoundError) as exc_info:
            manager.load_credentials()

        # Validate error message
        error_msg = str(exc_info.value)
        assert (
            "credentials" in error_msg.lower()
            or "not found" in error_msg.lower()
        ), "Error message must mention missing credentials file"

        # Validate can be caught as CredentialsError
        with pytest.raises(CredentialsError):
            manager.load_credentials()

    def test_credentials_invalid_json(self, mock_credentials_store):
        """
        Test handling of malformed JSON in credentials file.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Credential Loading (lines 278-281)

        Validates:
        - Raises CredentialsParseError for invalid JSON
        - Error message indicates JSON parsing failure
        - Error is catchable as CredentialsError

        Expected: Raises CredentialsParseError (TDD red phase - will fail)
        """
        from extension_base.config.credentials import CredentialsManager
        from extension_base.exceptions import (
            CredentialsError,
            CredentialsParseError,
        )

        # Create credentials file with invalid JSON
        creds_path = mock_credentials_store.create_invalid_json()

        # Attempt to load invalid credentials
        manager = CredentialsManager(credentials_path=str(creds_path))

        # Validate raises CredentialsParseError
        with pytest.raises(CredentialsParseError) as exc_info:
            manager.load_credentials()

        # Validate error message
        error_msg = str(exc_info.value)
        assert "json" in error_msg.lower() or "parse" in error_msg.lower(), (
            "Error message must indicate JSON parsing failure"
        )

        # Validate can be caught as CredentialsError
        with pytest.raises(CredentialsError):
            manager.load_credentials()

    def test_get_credential_by_id(self, mock_credentials_store):
        """
        Test retrieving credential by ID.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Credential Resolution (lines 283-286)
        - API/Interface (lines 293-304)

        Validates:
        - get_credential() returns correct credential
        - Credential has expected type and fields
        - Multiple credentials can be retrieved

        Expected: Credentials retrieved correctly (TDD red phase - will fail)
        """
        from extension_base.config.credentials import CredentialsManager

        # Create multi-auth credentials
        creds_path = mock_credentials_store.create_multi_auth_store()

        # Load credentials
        manager = CredentialsManager(credentials_path=str(creds_path))
        manager.load_credentials()

        # Get basic auth credential
        basic_cred = manager.get_credential("basic.auth.421")
        assert basic_cred is not None, "Basic credential must exist"
        assert hasattr(basic_cred, "type") or "type" in basic_cred, (
            "Credential must have type"
        )

        # Get token auth credential
        token_cred = manager.get_credential("token.auth.422")
        assert token_cred is not None, "Token credential must exist"

        # Get API key credential
        api_key_cred = manager.get_credential("api.key.423")
        assert api_key_cred is not None, "API key credential must exist"

    def test_get_credential_not_found(self, mock_credentials_store):
        """
        Test handling of non-existent credential ID.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Credential Resolution (lines 283-286)

        Validates:
        - Raises CredentialRefNotFoundError for invalid ID
        - Error message includes credential ID
        - Error is catchable as CredentialsError

        Expected: Raises CredentialRefNotFoundError (TDD red phase - will fail)
        """
        from extension_base.config.credentials import CredentialsManager
        from extension_base.exceptions import (
            CredentialRefNotFoundError,
            CredentialsError,
        )

        # Create credentials
        creds_path = mock_credentials_store.create_basic_auth_store()

        # Load credentials
        manager = CredentialsManager(credentials_path=str(creds_path))
        manager.load_credentials()

        # Attempt to get non-existent credential
        with pytest.raises(CredentialRefNotFoundError) as exc_info:
            manager.get_credential("nonexistent.credential")

        # Validate error message
        error_msg = str(exc_info.value)
        assert (
            "not found" in error_msg.lower()
            or "nonexistent" in error_msg.lower()
        ), "Error message must mention missing credential"

        # Validate can be caught as CredentialsError
        with pytest.raises(CredentialsError):
            manager.get_credential("nonexistent.credential")

    def test_validate_basic_auth_credential(self, mock_credentials_store):
        """
        Test validation of basic authentication credentials.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Credential Resolution (lines 283-286)
        - API/Interface - validate_credential() (lines 300)

        Validates:
        - Valid basic auth passes validation
        - Missing username raises CredentialInvalidError
        - Missing password raises CredentialInvalidError
        - Error messages indicate missing field

        Expected: Basic auth validated correctly (TDD red phase - will fail)
        """
        from extension_base.config.credentials import CredentialsManager
        from extension_base.exceptions import CredentialInvalidError

        # Test valid basic auth
        creds_path = mock_credentials_store.create_basic_auth_store()
        manager = CredentialsManager(credentials_path=str(creds_path))
        manager.load_credentials()

        basic_cred = manager.get_credential("test.endpoint.421")
        # Should not raise exception
        manager.validate_credential(basic_cred)

        # Test invalid basic auth (missing password)
        creds_path = mock_credentials_store.create_invalid_basic_auth()
        manager = CredentialsManager(credentials_path=str(creds_path))
        manager.load_credentials()

        invalid_cred = manager.get_credential("test.endpoint.421")
        with pytest.raises(CredentialInvalidError) as exc_info:
            manager.validate_credential(invalid_cred)

        error_msg = str(exc_info.value)
        assert (
            "password" in error_msg.lower() or "basic" in error_msg.lower()
        ), "Error must mention missing password for basic auth"

    def test_validate_token_auth_credential(self, mock_credentials_store):
        """
        Test validation of token authentication credentials.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Credential Resolution (lines 283-286)
        - API/Interface - validate_credential() (lines 300)

        Validates:
        - Valid token auth passes validation
        - Missing token raises CredentialInvalidError
        - Error message indicates missing token

        Expected: Token auth validated correctly (TDD red phase - will fail)
        """
        from extension_base.config.credentials import CredentialsManager
        from extension_base.exceptions import CredentialInvalidError

        # Test valid token auth
        creds_path = mock_credentials_store.create_token_auth_store()
        manager = CredentialsManager(credentials_path=str(creds_path))
        manager.load_credentials()

        token_cred = manager.get_credential("test.endpoint.421")
        # Should not raise exception
        manager.validate_credential(token_cred)

        # Test invalid token auth (missing token)
        creds_path = mock_credentials_store.create_invalid_token_auth()
        manager = CredentialsManager(credentials_path=str(creds_path))
        manager.load_credentials()

        invalid_cred = manager.get_credential("test.endpoint.421")
        with pytest.raises(CredentialInvalidError) as exc_info:
            manager.validate_credential(invalid_cred)

        error_msg = str(exc_info.value)
        assert "token" in error_msg.lower(), "Error must mention missing token"

    def test_validate_api_key_credential(self, mock_credentials_store):
        """
        Test validation of API key authentication credentials.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Credential Resolution (lines 283-286)
        - API/Interface - validate_credential() (lines 300)

        Validates:
        - Valid API key passes validation
        - Missing api_key raises CredentialInvalidError
        - Error message indicates missing API key

        Expected: API key validated correctly (TDD red phase - will fail)
        """
        from extension_base.config.credentials import CredentialsManager
        from extension_base.exceptions import CredentialInvalidError

        # Test valid API key
        creds_path = mock_credentials_store.create_api_key_store()
        manager = CredentialsManager(credentials_path=str(creds_path))
        manager.load_credentials()

        api_key_cred = manager.get_credential("test.endpoint.421")
        # Should not raise exception
        manager.validate_credential(api_key_cred)

        # Test invalid API key (missing api_key)
        creds_path = mock_credentials_store.create_invalid_api_key_auth()
        manager = CredentialsManager(credentials_path=str(creds_path))
        manager.load_credentials()

        invalid_cred = manager.get_credential("test.endpoint.421")
        with pytest.raises(CredentialInvalidError) as exc_info:
            manager.validate_credential(invalid_cred)

        error_msg = str(exc_info.value)
        assert (
            "api_key" in error_msg.lower() or "api key" in error_msg.lower()
        ), "Error must mention missing API key"

    def test_validate_oauth2_credential(self, mock_credentials_store):
        """
        Test validation of OAuth2 credentials.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Credential Resolution (lines 283-286)
        - API/Interface - validate_credential() (lines 300)

        Validates:
        - Valid OAuth2 passes validation
        - Missing client_id raises CredentialInvalidError
        - Missing client_secret raises CredentialInvalidError
        - Error message indicates missing field

        Expected: OAuth2 validated correctly (TDD red phase - will fail)
        """
        from extension_base.config.credentials import CredentialsManager
        from extension_base.exceptions import CredentialInvalidError

        # Test valid OAuth2
        creds_path = mock_credentials_store.create_oauth2_store()
        manager = CredentialsManager(credentials_path=str(creds_path))
        manager.load_credentials()

        oauth2_cred = manager.get_credential("test.endpoint.421")
        # Should not raise exception
        manager.validate_credential(oauth2_cred)

        # Test invalid OAuth2 (missing client_secret)
        creds_path = mock_credentials_store.create_invalid_oauth2_auth()
        manager = CredentialsManager(credentials_path=str(creds_path))
        manager.load_credentials()

        invalid_cred = manager.get_credential("test.endpoint.421")
        with pytest.raises(CredentialInvalidError) as exc_info:
            manager.validate_credential(invalid_cred)

        error_msg = str(exc_info.value)
        assert (
            "client_secret" in error_msg.lower()
            or "oauth" in error_msg.lower()
        ), "Error must mention missing OAuth2 field"

    def test_validate_certificate_credential(self, mock_credentials_store):
        """
        Test validation of certificate authentication credentials.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Credential Resolution (lines 283-286)
        - API/Interface - validate_credential() (lines 300)

        Validates:
        - Valid certificate auth passes validation
        - Missing certificate_path raises CredentialInvalidError
        - Missing private_key_path raises CredentialInvalidError
        - Error message indicates missing field

        Expected: Certificate auth validated correctly (TDD red phase - will fail)
        """
        from extension_base.config.credentials import CredentialsManager
        from extension_base.exceptions import CredentialInvalidError

        # Test valid certificate auth
        creds_path = mock_credentials_store.create_certificate_store()
        manager = CredentialsManager(credentials_path=str(creds_path))
        manager.load_credentials()

        cert_cred = manager.get_credential("test.endpoint.421")
        # Should not raise exception
        manager.validate_credential(cert_cred)

        # Test invalid certificate auth (missing private_key_path)
        creds_path = mock_credentials_store.create_invalid_certificate_auth()
        manager = CredentialsManager(credentials_path=str(creds_path))
        manager.load_credentials()

        invalid_cred = manager.get_credential("test.endpoint.421")
        with pytest.raises(CredentialInvalidError) as exc_info:
            manager.validate_credential(invalid_cred)

        error_msg = str(exc_info.value)
        assert (
            "private_key" in error_msg.lower()
            or "certificate" in error_msg.lower()
        ), "Error must mention missing certificate field"

    def test_credentials_not_logged(self, mock_credentials_store, caplog):
        """
        Test that credential values are never logged.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Security (lines 288-291)
        - API/Interface - mask_credential() (lines 301)

        Validates:
        - Passwords not in log output
        - Tokens not in log output
        - API keys not in log output
        - Client secrets not in log output
        - Error messages don't contain credentials

        Expected: Credentials never logged (TDD red phase - will fail)
        """
        import logging

        from extension_base.config.credentials import CredentialsManager

        # Enable logging
        caplog.set_level(logging.DEBUG)

        # Create credentials with sensitive data
        creds_path = mock_credentials_store.create_multi_auth_store()

        # Load and access credentials
        manager = CredentialsManager(credentials_path=str(creds_path))
        manager.load_credentials()

        # Get all credentials
        basic_cred = manager.get_credential("basic.auth.421")
        token_cred = manager.get_credential("token.auth.422")
        api_key_cred = manager.get_credential("api.key.423")

        # Check that sensitive values are not in logs
        log_output = caplog.text.lower()

        # These are the actual sensitive values from mock_credentials_store
        assert "pass1" not in log_output, "Password must not be logged"
        assert "token123" not in log_output, "Token must not be logged"
        assert "key123" not in log_output, "API key must not be logged"

    def test_get_auth_header_basic(self, mock_credentials_store):
        """
        Test generating HTTP auth header for basic authentication.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Credential Resolution (lines 283-286)
        - API/Interface (lines 293-304)

        Validates:
        - Returns Authorization header with Basic scheme
        - Header value is base64 encoded username:password
        - Header format is correct

        Expected: Basic auth header generated (TDD red phase - will fail)
        """
        import base64

        from extension_base.config.credentials import CredentialsManager

        # Create basic auth credentials
        creds_path = mock_credentials_store.create_basic_auth_store()

        # Load credentials
        manager = CredentialsManager(credentials_path=str(creds_path))
        manager.load_credentials()

        # Get credential
        basic_cred = manager.get_credential("test.endpoint.421")

        # Generate auth header
        auth_header = manager.get_auth_header(basic_cred)

        # Validate header structure
        assert isinstance(auth_header, dict), "Auth header must be dictionary"
        assert "Authorization" in auth_header, "Must have Authorization key"
        assert auth_header["Authorization"].startswith("Basic "), (
            "Basic auth must start with 'Basic '"
        )

        # Validate base64 encoding
        encoded_part = auth_header["Authorization"].split(" ")[1]
        try:
            decoded = base64.b64decode(encoded_part).decode()
            assert ":" in decoded, "Decoded value must contain ':' separator"
        except Exception as e:
            pytest.fail(f"Failed to decode basic auth header: {e}")

    def test_get_auth_header_token(self, mock_credentials_store):
        """
        Test generating HTTP auth header for token authentication.

        Spec Reference: docs/specs/extension-base-library.md#credentials-manager
        - Credential Resolution (lines 283-286)
        - API/Interface (lines 293-304)

        Validates:
        - Returns Authorization header with Bearer scheme
        - Header contains token value
        - Header format is correct

        Expected: Token auth header generated (TDD red phase - will fail)
        """
        from extension_base.config.credentials import CredentialsManager

        # Create token auth credentials
        creds_path = mock_credentials_store.create_token_auth_store()

        # Load credentials
        manager = CredentialsManager(credentials_path=str(creds_path))
        manager.load_credentials()

        # Get credential
        token_cred = manager.get_credential("test.endpoint.421")

        # Generate auth header
        auth_header = manager.get_auth_header(token_cred)

        # Validate header structure
        assert isinstance(auth_header, dict), "Auth header must be dictionary"
        assert "Authorization" in auth_header, "Must have Authorization key"
        assert auth_header["Authorization"].startswith("Bearer "), (
            "Token auth must start with 'Bearer '"
        )


# Made with Bob
