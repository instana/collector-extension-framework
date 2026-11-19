# (c) Copyright IBM Corp. 2026
"""
Pydantic v2 data models for extension configuration.

These models represent the validated, deserialized form of the
extension-config.json and credentials.json files.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from extension_base.exceptions import ConfigError, CredentialRefNotFoundError


class CredentialEntry(BaseModel):
    """A single credential record from credentials.json."""

    model_config = ConfigDict(extra="allow")

    type: str
    username: str | None = None
    password: str | None = None
    token: str | None = None
    api_key: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    certificate_path: str | None = None
    private_key_path: str | None = None

    def __repr__(self) -> str:
        masked = self.model_dump()
        for field in ("password", "token", "api_key", "client_secret"):
            if masked.get(field) is not None:
                masked[field] = "***"
        return f"CredentialEntry({masked})"

    def __str__(self) -> str:
        return self.__repr__()


class Endpoint(BaseModel):
    """A single monitored endpoint entry."""

    model_config = ConfigDict(extra="allow")

    id: str
    url: str
    credentials_ref: str
    # Populated by ConfigLoader after loading; not part of JSON schema
    credentials: CredentialEntry | None = Field(default=None, exclude=True)
    port: int | None = None
    interval: int | None = None
    timeout: int | None = None
    enabled: bool = True
    tags: dict[str, str] = Field(default_factory=dict)


class Configuration(BaseModel):
    """The 'configuration' block of extension-config.json."""

    model_config = ConfigDict(extra="allow")

    endpoints: list[Endpoint]
    interval: int | None = None
    timeout: int | None = None
    log_level: str = "INFO"


class OTLPConfiguration(BaseModel):
    """The 'otlp' block of extension-config.json."""

    model_config = ConfigDict(extra="allow")

    endpoint: str = "localhost:4317"
    protocol: str = "grpc"
    compression: str = "gzip"
    interval: int = 60
    timeout: int = 10
    instana_key: str | None = None
    tls: bool | None = None
    certificate_file: str | None = None
    http_proxy: str | None = None
    https_proxy: str | None = None
    no_proxy: str | None = None


class ExtensionConfig(BaseModel):
    """Root configuration object returned by ConfigLoader.load()."""

    model_config = ConfigDict(extra="allow")

    extension_id: str
    extension_name: str
    extension_version: str
    configuration: Configuration
    otlp: OTLPConfiguration = Field(default_factory=OTLPConfiguration)
    container_id: str | None = None
    supervisor_id: str | None = None
    deployment_id: str | None = None

    def get_endpoint_config(self, endpoint_id: str) -> Endpoint:
        """Return the Endpoint with the given id.

        Raises:
            ConfigError: if the endpoint_id is not found.
        """
        for ep in self.configuration.endpoints:
            if ep.id == endpoint_id:
                return ep
        raise ConfigError(
            f"Endpoint '{endpoint_id}' not found in configuration"
        )

    def get_credentials(self, endpoint_id: str) -> CredentialEntry:
        """Return the resolved CredentialEntry for the given endpoint id.

        Raises:
            CredentialRefNotFoundError: if no credentials are attached to
                the endpoint or the endpoint itself does not exist.
        """
        try:
            ep = self.get_endpoint_config(endpoint_id)
        except ConfigError:
            raise CredentialRefNotFoundError(
                f"Credential not found for endpoint '{endpoint_id}'"
            )
        if ep.credentials is None:
            raise CredentialRefNotFoundError(
                f"Credential not found for endpoint '{endpoint_id}'"
            )
        return ep.credentials

    def __str__(self) -> str:
        """Return a string representation that masks all credential values."""
        safe: dict[str, Any] = {
            "extension_id": self.extension_id,
            "extension_name": self.extension_name,
            "extension_version": self.extension_version,
            "container_id": self.container_id,
            "supervisor_id": self.supervisor_id,
            "deployment_id": self.deployment_id,
            "otlp": self.otlp.model_dump(),
            "configuration": {
                "log_level": self.configuration.log_level,
                "interval": self.configuration.interval,
                "timeout": self.configuration.timeout,
                "endpoints": [
                    {
                        "id": ep.id,
                        "url": ep.url,
                        "credentials_ref": ep.credentials_ref,
                    }
                    for ep in self.configuration.endpoints
                ],
            },
        }
        return f"ExtensionConfig({safe})"
