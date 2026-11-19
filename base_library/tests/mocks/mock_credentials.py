# (c) Copyright IBM Corp. 2026
"""
Mock credentials store generator for testing.

Provides utilities to create temporary credentials files with various
authentication types (basic, token, API key, OAuth2, certificate) for
testing the credentials manager.
"""

import json
import tempfile
from pathlib import Path
from typing import Any


class MockCredentialsStore:
    """
    Creates temporary credentials store files for testing.

    Supports creating credentials for all authentication types:
    - Basic authentication (username/password)
    - Token authentication (bearer token)
    - API key authentication
    - OAuth2 (client_id/client_secret)
    - Certificate authentication (certificate/private key paths)
    """

    def __init__(self, temp_dir: Path | None = None):
        """
        Initialize mock credentials store generator.

        Args:
            temp_dir: Optional temporary directory to use. If None, creates one.
        """
        self.temp_dir = temp_dir or Path(tempfile.mkdtemp())
        self.creds_files = []

    def create_basic_auth_store(
        self, extra_entries: dict | None = None
    ) -> Path:
        """
        Create a credentials store with basic authentication.

        Args:
            extra_entries: Optional extra credential entries to merge into the store.

        Returns:
            Path to the created credentials file
        """
        credentials = {
            "test.endpoint.421": {
                "type": "basic",
                "username": "testuser",
                "password": "testpass123",
            },
            **(extra_entries or {}),
        }

        return self._write_credentials(credentials, "basic_auth.json")

    def create_token_auth_store(self) -> Path:
        """
        Create a credentials store with token authentication.

        Returns:
            Path to the created credentials file
        """
        credentials = {
            "test.endpoint.421": {
                "type": "token",
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
            }
        }

        return self._write_credentials(credentials, "token_auth.json")

    def create_api_key_store(self) -> Path:
        """
        Create a credentials store with API key authentication.

        Returns:
            Path to the created credentials file
        """
        credentials = {
            "test.endpoint.421": {
                "type": "api_key",
                "api_key": "ak_live_1234567890abcdef",
            }
        }

        return self._write_credentials(credentials, "api_key_auth.json")

    def create_oauth2_store(self) -> Path:
        """
        Create a credentials store with OAuth2 authentication.

        Returns:
            Path to the created credentials file
        """
        credentials = {
            "test.endpoint.421": {
                "type": "oauth2",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
            }
        }

        return self._write_credentials(credentials, "oauth2_auth.json")

    def create_certificate_store(self) -> Path:
        """
        Create a credentials store with certificate authentication.

        Returns:
            Path to the created credentials file
        """
        credentials = {
            "test.endpoint.421": {
                "type": "certificate",
                "certificate_path": "/path/to/cert.pem",
                "private_key_path": "/path/to/key.pem",
            }
        }

        return self._write_credentials(credentials, "certificate_auth.json")

    def create_multi_auth_store(self) -> Path:
        """
        Create a credentials store with multiple authentication types.

        Returns:
            Path to the created credentials file
        """
        credentials = {
            "basic.auth.421": {
                "type": "basic",
                "username": "user1",
                "password": "pass1",
            },
            "token.auth.422": {"type": "token", "token": "token123"},
            "api.key.423": {"type": "api_key", "api_key": "key123"},
        }

        return self._write_credentials(credentials, "multi_auth.json")

    def create_invalid_basic_auth(self) -> Path:
        """
        Create a credentials store with invalid basic auth (missing password).

        Returns:
            Path to the created credentials file
        """
        credentials = {
            "test.endpoint.421": {
                "type": "basic",
                "username": "testuser",
                # Missing password field
            }
        }

        return self._write_credentials(credentials, "invalid_basic_auth.json")

    def create_invalid_token_auth(self) -> Path:
        """
        Create a credentials store with invalid token auth (missing token).

        Returns:
            Path to the created credentials file
        """
        credentials = {
            "test.endpoint.421": {
                "type": "token"
                # Missing token field
            }
        }

        return self._write_credentials(credentials, "invalid_token_auth.json")

    def create_invalid_api_key_auth(self) -> Path:
        """
        Create a credentials store with invalid API key auth (missing api_key).

        Returns:
            Path to the created credentials file
        """
        credentials = {
            "test.endpoint.421": {
                "type": "api_key"
                # Missing api_key field
            }
        }

        return self._write_credentials(
            credentials, "invalid_api_key_auth.json"
        )

    def create_invalid_oauth2_auth(self) -> Path:
        """
        Create a credentials store with invalid OAuth2 (missing client_secret).

        Returns:
            Path to the created credentials file
        """
        credentials = {
            "test.endpoint.421": {
                "type": "oauth2",
                "client_id": "test_client_id",
                # Missing client_secret field
            }
        }

        return self._write_credentials(credentials, "invalid_oauth2_auth.json")

    def create_invalid_certificate_auth(self) -> Path:
        """
        Create a credentials store with invalid certificate auth (missing private_key_path).

        Returns:
            Path to the created credentials file
        """
        credentials = {
            "test.endpoint.421": {
                "type": "certificate",
                "certificate_path": "/path/to/cert.pem",
                # Missing private_key_path field
            }
        }

        return self._write_credentials(
            credentials, "invalid_certificate_auth.json"
        )

    def create_empty_store(self) -> Path:
        """
        Create an empty credentials store.

        Returns:
            Path to the created credentials file
        """
        credentials = {}

        return self._write_credentials(credentials, "empty_store.json")

    def create_invalid_json(self) -> Path:
        """
        Create a file with invalid JSON syntax.

        Returns:
            Path to the created file with invalid JSON
        """
        invalid_json = '{"test.endpoint.421": {"type": "basic", "invalid": }}'

        creds_path = self.temp_dir / "invalid_json.json"
        creds_path.write_text(invalid_json)
        self.creds_files.append(creds_path)

        return creds_path

    def _write_credentials(
        self, credentials: dict[str, Any], filename: str
    ) -> Path:
        """
        Write credentials dictionary to a JSON file.

        Args:
            credentials: Credentials dictionary
            filename: Name of the file to create

        Returns:
            Path to the created file
        """
        creds_path = self.temp_dir / filename
        creds_path.write_text(json.dumps(credentials, indent=2))
        self.creds_files.append(creds_path)

        return creds_path

    def cleanup(self):
        """Remove all created credentials files."""
        for creds_file in self.creds_files:
            if creds_file.exists():
                creds_file.unlink()
        self.creds_files.clear()


def create_basic_auth_credentials() -> dict[str, Any]:
    """
    Helper function to create basic auth credentials dictionary.

    Returns:
        Basic auth credentials dictionary
    """
    return {
        "test.endpoint.421": {
            "type": "basic",
            "username": "testuser",
            "password": "testpass123",
        }
    }


# Made with Bob
