# (c) Copyright IBM Corp. 2026
"""
Configuration loader for Extension Base Library.

Reads extension-config.json, validates required fields, resolves
credential references, applies environment variable overrides, and
applies default values before returning a fully populated ExtensionConfig.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from extension_base.config.credentials import CredentialsManager
from extension_base.config.models import (
    Configuration,
    CredentialEntry,
    Endpoint,
    ExtensionConfig,
    OTLPConfiguration,
)
from extension_base.exceptions import (
    ConfigNotFoundError,
    ConfigParseError,
    ConfigValidationError,
)

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = (
    "/opt/instana/custom-collector/config/extension-config.json"
)
_DEFAULT_CREDS_PATH = "/opt/instana/custom-collector/config/credentials.json"

# Top-level required fields
_REQUIRED_TOP = (
    "extension_id",
    "extension_name",
    "extension_version",
    "configuration",
)

# Environment variable → (section, field, convert_fn)
# convert_fn converts the raw string value to the correct Python type.
_ENV_OVERRIDES: list[tuple[str, str, str, object]] = [
    # (env_var, section, field, converter)
    ("EXTENSION_LOG_LEVEL", "configuration", "log_level", str),
    ("OTLP_ENDPOINT", "otlp", "endpoint", str),
    ("CONTAINER_ID", "root", "container_id", str),
    ("SUPERVISOR_ID", "root", "supervisor_id", str),
    # OTEL standard env vars — endpoint (last one wins if both set)
    ("OTEL_EXPORTER_OTLP_ENDPOINT", "otlp", "endpoint", str),
    (
        "OTEL_EXPORTER_OTLP_TIMEOUT",
        "otlp",
        "timeout",
        lambda v: int(int(v) / 1000),
    ),
    ("OTEL_EXPORTER_OTLP_PROTOCOL", "otlp", "protocol", str),
    ("OTEL_EXPORTER_OTLP_COMPRESSION", "otlp", "compression", str),
    (
        "OTEL_METRIC_EXPORT_INTERVAL",
        "otlp",
        "interval",
        lambda v: int(int(v) / 1000),
    ),
    # Instana backend key — injected as x-instana-key HTTP header
    ("INSTANA_KEY", "otlp", "instana_key", str),
    # Explicit TLS toggle — overrides the instana_key-presence heuristic
    ("OTLP_TLS", "otlp", "tls", lambda v: v.strip().lower() == "true"),
]


class ConfigLoader:
    """Loads, validates, and resolves the extension configuration."""

    def __init__(
        self,
        config_path: str = _DEFAULT_CONFIG_PATH,
        credentials_path: str = _DEFAULT_CREDS_PATH,
    ) -> None:
        self._config_path = config_path
        self._credentials_path = credentials_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> ExtensionConfig:
        """Load, validate, and return the fully resolved ExtensionConfig.

        Raises:
            ConfigNotFoundError: config file does not exist.
            ConfigParseError: config file contains invalid JSON.
            ConfigValidationError: required fields missing or constraints violated.
            CredentialsFileNotFoundError: credentials file does not exist.
            CredentialsParseError: credentials file contains invalid JSON.
            CredentialRefNotFoundError: endpoint references unknown credential.
            CredentialInvalidError: credential is missing required fields.
        """
        # Step 1 — read and parse config file
        data = self._read_config()

        # Step 2 — validate required top-level fields (structural only)
        self._validate_required_fields(data)

        # Step 3 — validate endpoint count (1–35)
        self._validate_endpoint_count(data)

        # Step 4 — apply environment variable overrides
        self._apply_env_overrides(data)

        # Step 5 — validate otlp.endpoint (before defaults so we can detect
        #           explicitly missing endpoint vs. not-present otlp block)
        self._validate_otlp_endpoint(data)

        # Step 6 — apply defaults
        self._apply_defaults(data)

        # Step 7 — load credentials
        creds_mgr = CredentialsManager(self._credentials_path)
        creds_mgr.load_credentials()

        # Step 8 — resolve credentials for each endpoint
        self._resolve_credentials(data, creds_mgr)

        # Step 9 — resolve backend key reference for OTLP block
        self._resolve_backend_key(data, creds_mgr)

        # Step 10 — build and return ExtensionConfig
        return self._build_config(data)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read_config(self) -> dict[str, Any]:
        path = Path(self._config_path)
        if not path.exists():
            raise ConfigNotFoundError(
                f"config.json not found: {self._config_path}"
            )
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigParseError(
                f"json parse error in config file: {exc}"
            ) from exc

    def _validate_required_fields(self, data: dict) -> None:
        for field in _REQUIRED_TOP:
            if field not in data:
                raise ConfigValidationError(
                    f"{field} is required in configuration"
                )

    def _validate_otlp_endpoint(self, data: dict) -> None:
        """Raise ConfigValidationError if the otlp block exists but has no endpoint.

        When the 'otlp' key is absent entirely, defaults will fill it later.
        When it is present (even as an empty dict), the endpoint field is
        required unless an environment variable supplies it.
        """
        if "otlp" not in data:
            return
        otlp = data["otlp"]
        if isinstance(otlp, dict) and "endpoint" not in otlp:
            env_endpoint = os.environ.get(
                "OTEL_EXPORTER_OTLP_ENDPOINT"
            ) or os.environ.get("OTLP_ENDPOINT")
            if not env_endpoint:
                raise ConfigValidationError(
                    "endpoint is required in otlp configuration"
                )

    def _validate_endpoint_count(self, data: dict) -> None:
        endpoints = data.get("configuration", {}).get("endpoints", [])
        if len(endpoints) < 1:
            raise ConfigValidationError(
                "at least one endpoint is required in configuration"
            )
        if len(endpoints) > 35:
            raise ConfigValidationError(
                f"maximum 35 endpoints allowed, got {len(endpoints)}"
            )

    def _resolve_credentials(
        self, data: dict, creds_mgr: CredentialsManager
    ) -> None:
        """Attach resolved CredentialEntry objects to each endpoint dict.

        Resolves credential references by ID only; validation of credential
        completeness is the caller's responsibility at collection time.
        """
        for ep in data.get("configuration", {}).get("endpoints", []):
            ref = ep.get("credentials_ref", "")
            cred = creds_mgr.get_credential(ref)
            creds_mgr.validate_credential(cred)
            ep["_resolved_credentials"] = cred

    def _resolve_backend_key(
        self, data: dict, creds_mgr: CredentialsManager
    ) -> None:
        """Resolve otlp.backend_key_ref to otlp.instana_key via the credentials store.

        When ``otlp.backend_key_ref`` is present and ``otlp.instana_key`` has
        not already been set (e.g. by an env-var override), the referenced
        credential is looked up and its ``api_key`` value is written into
        ``otlp.instana_key`` so the rest of the pipeline requires no changes.

        Raises:
            CredentialRefNotFoundError: the referenced credential ID is absent.
            CredentialInvalidError: the credential exists but has no api_key.
        """
        otlp = data.get("otlp", {})
        ref = otlp.get("backend_key_ref")
        if not ref:
            return
        # Env-var override already won; nothing to do.
        if otlp.get("instana_key"):
            return
        cred = creds_mgr.get_credential(ref)
        creds_mgr.validate_credential(cred)
        otlp["instana_key"] = cred.api_key

    def _apply_env_overrides(self, data: dict) -> None:
        for env_var, section, field, converter in _ENV_OVERRIDES:
            raw = os.environ.get(env_var)
            if raw is None:
                continue
            try:
                value = converter(raw)  # type: ignore[operator]
            except (ValueError, TypeError):
                continue
            if section == "root":
                data[field] = value
            elif section == "otlp":
                data.setdefault("otlp", {})[field] = value
            elif section == "configuration":
                data.setdefault("configuration", {})[field] = value

    def _apply_defaults(self, data: dict) -> None:
        # OTLP defaults
        otlp = data.setdefault("otlp", {})
        otlp.setdefault("endpoint", "localhost:4317")
        otlp.setdefault("protocol", "grpc")
        otlp.setdefault("compression", "gzip")
        otlp.setdefault("interval", 60)
        otlp.setdefault("timeout", 10)

        # Configuration defaults
        cfg = data.setdefault("configuration", {})
        cfg.setdefault("log_level", "INFO")
        # Ensure configuration.interval has a value (inherit from otlp.interval)
        cfg.setdefault("interval", otlp["interval"])

        # Propagate configuration.interval / timeout to endpoints that lack them
        cfg_interval = cfg.get("interval")
        cfg_timeout = cfg.get("timeout")
        for ep in cfg.get("endpoints", []):
            if ep.get("interval") is None and cfg_interval is not None:
                ep["interval"] = cfg_interval
            if ep.get("timeout") is None and cfg_timeout is not None:
                ep["timeout"] = cfg_timeout

    def _build_config(self, data: dict) -> ExtensionConfig:
        """Construct ExtensionConfig from the fully processed data dict."""
        # Build Endpoint objects, reattaching resolved credentials
        raw_endpoints = data["configuration"].get("endpoints", [])
        endpoints: list[Endpoint] = []
        for raw_ep in raw_endpoints:
            resolved: CredentialEntry | None = raw_ep.pop(
                "_resolved_credentials", None
            )
            ep = Endpoint.model_validate(raw_ep)
            ep.credentials = resolved
            endpoints.append(ep)

        configuration = Configuration.model_validate(
            {**data["configuration"], "endpoints": endpoints}
        )
        otlp = OTLPConfiguration.model_validate(data.get("otlp", {}))

        return ExtensionConfig(
            extension_id=data["extension_id"],
            extension_name=data["extension_name"],
            extension_version=data["extension_version"],
            configuration=configuration,
            otlp=otlp,
            container_id=data.get("container_id"),
            supervisor_id=data.get("supervisor_id"),
            deployment_id=data.get("deployment_id"),
        )
