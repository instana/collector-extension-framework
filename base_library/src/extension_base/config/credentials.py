# (c) Copyright IBM Corp. 2026
"""
Credentials manager for Extension Base Library.

Handles secure credential loading, resolution, and validation without
ever logging sensitive values such as passwords, tokens, or API keys.
"""

import base64
import json
import logging
from pathlib import Path

from extension_base.config.models import CredentialEntry
from extension_base.exceptions import (
    CredentialInvalidError,
    CredentialRefNotFoundError,
    CredentialsFileNotFoundError,
    CredentialsParseError,
)

logger = logging.getLogger(__name__)

_SENSITIVE_FIELDS = ("password", "token", "api_key", "client_secret")

# Required fields per credential type — (field_name, error_keyword)
_REQUIRED_FIELDS: dict[str, list[tuple[str, str]]] = {
    "basic": [("password", "password")],
    "token": [("token", "token")],
    "api_key": [("api_key", "api_key")],
    "oauth2": [("client_secret", "client_secret")],
    "certificate": [("private_key_path", "private_key")],
}


class CredentialsManager:
    """Loads and manages credentials from a JSON credentials store."""

    DEFAULT_PATH = "/opt/instana/custom-collector/config/credentials.json"

    def __init__(
        self, credentials_path: str = DEFAULT_PATH
    ) -> None:
        self._credentials_path = credentials_path
        self._store: dict[str, CredentialEntry] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_credentials(self) -> dict[str, CredentialEntry]:
        """Load credentials from the credentials JSON file.

        Returns:
            Mapping of credential ID → CredentialEntry.

        Raises:
            CredentialsFileNotFoundError: file does not exist.
            CredentialsParseError: file contains invalid JSON.
        """
        path = Path(self._credentials_path)
        if not path.exists():
            raise CredentialsFileNotFoundError(
                f"credentials file not found: {self._credentials_path}"
            )

        try:
            raw: dict = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CredentialsParseError(
                f"json parse error in credentials file: {exc}"
            ) from exc

        self._store = {
            cred_id: CredentialEntry(**entry)
            for cred_id, entry in raw.items()
        }
        # Log only IDs — never log credential values
        logger.debug(
            "Loaded %d credential(s): %s",
            len(self._store),
            list(self._store.keys()),
        )
        return self._store

    def get_credential(self, credential_id: str) -> CredentialEntry:
        """Return the CredentialEntry for *credential_id*.

        Raises:
            CredentialRefNotFoundError: ID not in store.
        """
        entry = self._store.get(credential_id)
        if entry is None:
            raise CredentialRefNotFoundError(
                f"Credential '{credential_id}' not found in store"
            )
        return entry

    def validate_credential(self, credential: CredentialEntry) -> None:
        """Validate that *credential* contains all required fields for its type.

        Raises:
            CredentialInvalidError: a required field is missing or empty.
        """
        checks = _REQUIRED_FIELDS.get(credential.type, [])
        for field_name, error_keyword in checks:
            value = getattr(credential, field_name, None)
            if not value:
                raise CredentialInvalidError(
                    f"{error_keyword} is required for {credential.type} credentials"
                )

    def get_auth_header(
        self, credential: CredentialEntry
    ) -> dict[str, str]:
        """Return an HTTP Authorization header dict for *credential*.

        Returns:
            ``{"Authorization": "Basic ..."}``,
            ``{"Authorization": "Bearer ..."}``, or ``{}`` for other types.
        """
        if credential.type == "basic":
            encoded = base64.b64encode(
                f"{credential.username}:{credential.password}".encode()
            ).decode()
            return {"Authorization": f"Basic {encoded}"}
        if credential.type == "token":
            return {"Authorization": f"Bearer {credential.token}"}
        return {}

    def mask_credential(self, credential: CredentialEntry) -> dict:
        """Return a copy of *credential* as a dict with sensitive values masked."""
        data = credential.model_dump()
        for field in _SENSITIVE_FIELDS:
            if data.get(field) is not None:
                data[field] = "***"
        return data
