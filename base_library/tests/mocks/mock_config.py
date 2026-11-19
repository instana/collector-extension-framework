# (c) Copyright IBM Corp. 2026
"""
Mock configuration file generator for testing.

Provides utilities to create temporary configuration files with various
scenarios (valid, invalid, missing fields, etc.) for testing the
configuration loader.
"""

import json
import tempfile
from pathlib import Path
from typing import Any


class MockConfigFile:
    """
    Creates temporary configuration files for testing.

    Supports creating valid configs, invalid configs, configs with missing
    fields, and configs with various edge cases.
    """

    def __init__(self, temp_dir: Path | None = None):
        """
        Initialize mock config file generator.

        Args:
            temp_dir: Optional temporary directory to use. If None, creates one.
        """
        self.temp_dir = temp_dir or Path(tempfile.mkdtemp())
        self.config_files = []

    def create_valid_config(self, extra_otlp: dict | None = None) -> Path:
        """
        Create a valid configuration file with all required fields.

        Args:
            extra_otlp: Optional extra fields to merge into the 'otlp' block.

        Returns:
            Path to the created config file
        """
        config = {
            "extension_id": "ext-123456",
            "extension_name": "test-extension",
            "extension_version": "1.0.0",
            "configuration": {
                "interval": 60,
                "timeout": 30,
                "log_level": "INFO",
                "endpoints": [
                    {
                        "id": "421",
                        "url": "https://example.com:8000",
                        "credentials_ref": "test.endpoint.421",
                        "interval": 15,
                        "enabled": True,
                        "tags": {"region": "US", "environment": "production"},
                    }
                ],
            },
            "otlp": {
                "endpoint": "localhost:4317",
                "interval": 60,
                "timeout": 10,
                "protocol": "grpc",
                "compression": "gzip",
                **(extra_otlp or {}),
            },
            "container_id": "container-1",
            "supervisor_id": "supervisor-vm-01",
            "deployment_id": "deploy-789",
        }

        return self._write_config(config, "valid_config.json")

    def create_valid_config_no_otlp(self) -> Path:
        """Create a valid config without an 'otlp' block.

        Used to prove that env-var overrides targeting otlp fields work
        even when the JSON file contains no 'otlp' key at all.
        """
        config = {
            "extension_id": "ext-123456",
            "extension_name": "test-extension",
            "extension_version": "1.0.0",
            "configuration": {
                "interval": 60,
                "timeout": 30,
                "log_level": "INFO",
                "endpoints": [
                    {
                        "id": "421",
                        "url": "https://example.com:8000",
                        "credentials_ref": "test.endpoint.421",
                        "interval": 15,
                        "enabled": True,
                        "tags": {},
                    }
                ],
            },
            "container_id": "container-1",
            "supervisor_id": "supervisor-vm-01",
            # No "otlp" key — endpoint must come entirely from env vars
        }
        return self._write_config(config, "valid_config_no_otlp.json")

    def create_invalid_json(self) -> Path:
        """
        Create a file with invalid JSON syntax.

        Returns:
            Path to the created file with invalid JSON
        """
        invalid_json = '{"extension_id": "test", "invalid": }'

        config_path = self.temp_dir / "invalid_json.json"
        config_path.write_text(invalid_json)
        self.config_files.append(config_path)

        return config_path

    def create_missing_field(self, field_name: str) -> Path:
        """
        Create a config file missing a specific required field.

        Args:
            field_name: Name of the field to omit (e.g., "extension_id", "otlp.endpoint")

        Returns:
            Path to the created config file
        """
        config = {
            "extension_id": "ext-123456",
            "extension_name": "test-extension",
            "extension_version": "1.0.0",
            "configuration": {
                "interval": 60,
                "timeout": 30,
                "endpoints": [
                    {
                        "id": "421",
                        "url": "https://example.com:8000",
                        "credentials_ref": "test.endpoint.421",
                    }
                ],
            },
            "otlp": {"endpoint": "localhost:4317"},
        }

        # Remove the specified field
        if field_name == "extension_id":
            del config["extension_id"]
        elif field_name == "extension_name":
            del config["extension_name"]
        elif field_name == "extension_version":
            del config["extension_version"]
        elif field_name == "configuration":
            del config["configuration"]
        elif field_name == "otlp.endpoint":
            del config["otlp"]["endpoint"]

        return self._write_config(
            config, f"missing_{field_name.replace('.', '_')}.json"
        )

    def create_multi_endpoint_config(self) -> Path:
        """
        Create a config with multiple endpoints using different auth types.

        Returns:
            Path to the created config file
        """
        config = {
            "extension_id": "ext-123456",
            "extension_name": "test-extension",
            "extension_version": "1.0.0",
            "configuration": {
                "interval": 60,
                "timeout": 30,
                "endpoints": [
                    {
                        "id": "421",
                        "url": "https://example1.com:8000",
                        "credentials_ref": "basic.auth.421",
                    },
                    {
                        "id": "422",
                        "url": "https://example2.com:8000",
                        "credentials_ref": "token.auth.422",
                    },
                ],
            },
            "otlp": {"endpoint": "localhost:4317"},
        }

        return self._write_config(config, "multi_endpoint.json")

    def create_invalid_credential_ref(self) -> Path:
        """
        Create a config with an invalid credential reference.

        Returns:
            Path to the created config file
        """
        config = {
            "extension_id": "ext-123456",
            "extension_name": "test-extension",
            "extension_version": "1.0.0",
            "configuration": {
                "interval": 60,
                "timeout": 30,
                "endpoints": [
                    {
                        "id": "421",
                        "url": "https://example.com:8000",
                        "credentials_ref": "nonexistent.credential.ref",
                    }
                ],
            },
            "otlp": {"endpoint": "localhost:4317"},
        }

        return self._write_config(config, "invalid_cred_ref.json")

    def create_minimal_config(self) -> Path:
        """
        Create a minimal config with only required fields.

        Returns:
            Path to the created config file
        """
        config = {
            "extension_id": "ext-123456",
            "extension_name": "test-extension",
            "extension_version": "1.0.0",
            "configuration": {
                "endpoints": [
                    {
                        "id": "421",
                        "url": "https://example.com:8000",
                        "credentials_ref": "test.endpoint.421",
                    }
                ]
            },
        }

        return self._write_config(config, "minimal_config.json")

    def create_config_with_endpoint_count(self, count: int) -> Path:
        """
        Create a config with a specific number of endpoints.

        Args:
            count: Number of endpoints to create (0-50)

        Returns:
            Path to the created config file
        """
        endpoints = []
        for i in range(count):
            endpoints.append(
                {
                    "id": str(400 + i),
                    "url": f"https://example{i}.com:8000",
                    "credentials_ref": f"test.endpoint.{400 + i}",
                }
            )

        config = {
            "extension_id": "ext-123456",
            "extension_name": "test-extension",
            "extension_version": "1.0.0",
            "configuration": {
                "interval": 60,
                "timeout": 30,
                "endpoints": endpoints,
            },
            "otlp": {"endpoint": "localhost:4317"},
        }

        return self._write_config(config, f"config_{count}_endpoints.json")

    def _write_config(self, config: dict[str, Any], filename: str) -> Path:
        """
        Write config dictionary to a JSON file.

        Args:
            config: Configuration dictionary
            filename: Name of the file to create

        Returns:
            Path to the created file
        """
        config_path = self.temp_dir / filename
        config_path.write_text(json.dumps(config, indent=2))
        self.config_files.append(config_path)

        return config_path

    def cleanup(self):
        """Remove all created config files."""
        for config_file in self.config_files:
            if config_file.exists():
                config_file.unlink()
        self.config_files.clear()


class _ConfigStr(str):
    """A string subclass that also supports attribute-style access.

    Behaves as a JSON string (so ``config_file.write_text(valid_config)``
    and ``json.loads(valid_config)`` work), while also exposing nested
    attributes (so ``valid_config.otlp.interval = 30`` works in tests).
    """

    class _Namespace:
        """Simple mutable namespace for nested attribute access."""

        def __init__(self, data: dict):
            for k, v in data.items():
                setattr(self, k, _ConfigStr._Namespace(v) if isinstance(v, dict) else v)

        def __repr__(self):
            return repr(self.__dict__)

    def __new__(cls, data: dict):
        import json as _json
        instance = super().__new__(cls, _json.dumps(data, indent=2))
        # Attach top-level keys as attributes
        for k, v in data.items():
            setattr(instance, k, cls._Namespace(v) if isinstance(v, dict) else v)
        return instance


def create_valid_config() -> "_ConfigStr":
    """
    Helper function to create a valid config string/object.

    Returns a :class:`_ConfigStr` that behaves as both a JSON string
    (for ``write_text`` / ``json.loads``) and an object with attribute
    access (for ``valid_config.otlp.interval = 30``).
    """
    return _ConfigStr({
        "extension_id": "ext-123456",
        "extension_name": "test-extension",
        "extension_version": "1.0.0",
        "configuration": {
            "interval": 60,
            "timeout": 30,
            "log_level": "INFO",
            "endpoints": [
                {
                    "id": "421",
                    "url": "https://example.com:8000",
                    "credentials_ref": "test.endpoint.421",
                    "interval": 15,
                    "enabled": True,
                    "tags": {"region": "US", "environment": "production"},
                }
            ],
        },
        "otlp": {
            "endpoint": "localhost:4317",
            "interval": 60,
            "timeout": 10,
            "protocol": "grpc",
            "compression": "gzip",
        },
        "container_id": "container-1",
        "supervisor_id": "supervisor-vm-01",
        "deployment_id": "deploy-789",
    })


# Made with Bob
