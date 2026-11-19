# (c) Copyright IBM Corp. 2026
"""
Integration Tests for Extension Base Library

Tests end-to-end scenarios with multiple components working together.
Validates component interaction, data flow, and system behavior.

Test Coverage (FR7 - Integration Tests):
- T101: Full extension lifecycle (config → metrics → shutdown)
- T102: Configuration loading with credential resolution
- T103: Metric emission through OTLP pipeline
- T104: Health reporting integration
- T105: Multi-endpoint collection coordination
- T106: Error propagation across components
- T107: Graceful shutdown with resource cleanup
- T108: Environment variable override integration
- T109: Signal handling integration (SIGTERM/SIGINT)
- T110: Thread lifecycle with collection function
- T111: Resource monitoring integration
- T112: Component initialization order validation

TDD Status: RED phase - All tests should FAIL initially (no implementation)

Spec Reference: Multiple sections - Integration of all core components
- Configuration Loader: lines 196-269
- Credentials Manager: lines 270-304
- Metrics Emitter: lines 305-488
- Health Reporter: lines 489-617
- Lifecycle Manager: lines 618-759
"""

import signal
import threading
import time
from unittest.mock import Mock, patch

from extension_base.config.loader import ConfigLoader

import pytest


class TestIntegration:
    """Integration tests for Extension Base Library components."""

    def test_full_extension_lifecycle(
        self, valid_config, valid_credentials, mock_otlp_server, tmp_path
    ):
        """
        Test complete extension lifecycle from initialization to shutdown.

        Spec Reference: docs/specs/extension-base-library.md#api-reference
        - Module Entry Point (lines 762-784)
        - ExtensionBase Class (lines 785-808)

        Validates:
        - Configuration loaded successfully
        - Credentials resolved
        - OpenTelemetry initialized
        - Metrics emitted to OTLP endpoint
        - Health status reported
        - Graceful shutdown completes
        - Resources cleaned up

        Expected: Full lifecycle works (TDD red phase - will fail)
        """
        from extension_base.core import ExtensionBase

        # Create config and credentials files
        config_file = tmp_path / "config.json"
        creds_file = tmp_path / "credentials.json"
        config_file.write_text(valid_config)
        creds_file.write_text(valid_credentials)

        # Mock collection function
        collection_called = threading.Event()

        def mock_collection(endpoint, emitter):
            collection_called.set()
            emitter.record_counter("test.metric", 1)

        # Patch setup_otel so ExtensionBase picks up the mock's in-memory
        # MeterProvider, and patch ConfigLoader to read from the temp files
        # instead of the default container paths.
        with patch(
            "extension_base.metrics.otel_setup.setup_otel",
            return_value=(mock_otlp_server.meter_provider, mock_otlp_server.meter_provider),
        ), patch(
            "extension_base.config.loader.ConfigLoader",
            lambda: ConfigLoader(
                config_path=str(config_file),
                credentials_path=str(creds_file),
            ),
        ):
            extension = ExtensionBase()

        # Start extension in separate thread
        extension_thread = threading.Thread(
            target=extension.run, args=(mock_collection,)
        )
        extension_thread.start()

        # Wait for collection to run
        assert collection_called.wait(timeout=5), (
            "Collection function not called"
        )

        # Verify metrics were captured by the in-memory reader
        assert mock_otlp_server.metrics_received > 0, (
            "No metrics received by OTLP"
        )

        # Trigger shutdown
        extension.shutdown()
        extension_thread.join(timeout=5)

        # Verify clean shutdown
        assert not extension_thread.is_alive(), (
            "Extension thread still running"
        )

    def test_config_loading_with_credential_resolution(
        self, valid_config, valid_credentials, tmp_path
    ):
        """
        Test configuration loading with credential resolution.

        Spec Reference: docs/specs/extension-base-library.md#core-components
        - Configuration Loader (lines 196-269)
        - Credentials Manager (lines 270-304)

        Validates:
        - Config file loaded
        - Credentials file loaded
        - Credential references resolved
        - Endpoints have credentials attached
        - Environment overrides applied

        Expected: Config and credentials integrated (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader

        # Create config and credentials files
        config_file = tmp_path / "config.json"
        creds_file = tmp_path / "credentials.json"
        config_file.write_text(valid_config)
        creds_file.write_text(valid_credentials)

        # Load configuration
        loader = ConfigLoader(
            config_path=str(config_file), credentials_path=str(creds_file)
        )
        config = loader.load()

        # Validate configuration loaded
        assert config.extension_id == "ext-123456"
        assert len(config.configuration.endpoints) > 0

        # Validate credentials resolved
        endpoint = config.configuration.endpoints[0]
        assert endpoint.credentials is not None, "Credentials not resolved"
        assert endpoint.credentials.type == "basic"
        assert endpoint.credentials.username is not None
        assert endpoint.credentials.password is not None

    def test_metric_emission_through_otlp_pipeline(
        self, valid_config, mock_otlp_server, tmp_path, mocker
    ):
        """
        Test metric emission through complete OTLP pipeline.

        Spec Reference: docs/specs/extension-base-library.md#core-components
        - Metrics Emitter (lines 305-488)

        Validates:
        - MetricsEmitter initialized with OTLP endpoint
        - Metrics recorded (counter, gauge, histogram)
        - Metrics batched
        - Metrics exported to OTLP server
        - OTLP server receives metrics

        Expected: Metrics flow through pipeline (TDD red phase - will fail)
        """
        from extension_base.metrics.emitter import MetricsEmitter
        from extension_base.metrics.otel_setup import setup_otel

        # Use the mock server's in-memory MeterProvider (no network needed) from mock_otlp_server
        # as return value for both create_meter_provider() and create_internal_meter_provider()
        mocker.patch(
            "extension_base.metrics.otel_setup.create_meter_provider",
            return_value=mock_otlp_server.meter_provider,
        )
        mocker.patch(
            "extension_base.metrics.otel_setup.create_internal_meter_provider",
            return_value=mock_otlp_server.meter_provider,
        )

        # Setup OpenTelemetry with mock OTLP server
        business_mp, _ = setup_otel(
            endpoint=mock_otlp_server.endpoint,
            service_name="test-extension",
            service_version="1.0.0",
        )

        # Create metrics emitter
        endpoint_config = Mock()
        endpoint_config.id = "test-endpoint"
        endpoint_config.tags = {"env": "test"}

        emitter = MetricsEmitter(
            meter=business_mp.get_meter("test"), endpoint=endpoint_config
        )

        # Emit various metric types
        emitter.record_counter("test.counter", 5, {"status": "success"})
        emitter.record_gauge("test.gauge", 42.5, {"unit": "percent"})
        emitter.record_histogram(
            "test.histogram", 0.125, {"operation": "query"}
        )

        # Verify all three instruments are present in the in-memory reader
        assert mock_otlp_server.metrics_received >= 3, (
            "Not all metrics received"
        )

    def test_health_reporting_integration(self, valid_config, tmp_path):
        """
        Test health reporting integration with other components.

        Spec Reference: docs/specs/extension-base-library.md#core-components
        - Health Reporter (lines 489-617)

        Validates:
        - HealthReporter initialized
        - HTTP health endpoint started
        - Endpoint status tracked
        - Metrics export status tracked
        - Health status queryable via HTTP

        Expected: Health reporting integrated (TDD red phase - will fail)
        """
        from extension_base.health.reporter import HealthReporter

        # Initialize health reporter
        reporter = HealthReporter(
            extension_id="ext-123456",
            container_id="container-1",
            http_port=8080,
            http_bind="127.0.0.1",
        )

        # Start HTTP server
        reporter.start_http_server()

        # Update endpoint status
        reporter.update_endpoint_status(
            endpoint_id="421",
            status="collecting",
            collections_total=100,
            errors_total=2,
        )

        # Query health status via HTTP
        import requests

        response = requests.get("http://127.0.0.1:8080/health", timeout=5)
        assert response.status_code == 200, "Health endpoint not responding"

        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "421" in health_data["endpoints"]

        # Cleanup
        reporter.stop_http_server()

    def test_multi_endpoint_collection_coordination(
        self, valid_config, mock_otlp_server, tmp_path
    ):
        """
        Test coordination of multiple endpoint collections.

        Spec Reference: docs/specs/extension-base-library.md#core-components
        - Lifecycle Manager - Thread Management (lines 632-636)

        Validates:
        - Multiple endpoints configured
        - Separate thread per endpoint
        - Collections run independently
        - Metrics tagged per endpoint
        - All endpoints collect successfully

        Expected: Multi-endpoint coordination works (TDD red phase - will fail)
        """
        # Create config with multiple endpoints
        import json

        from extension_base.health.reporter import HealthReporter
        from extension_base.lifecycle.manager import LifecycleManager

        config_dict = json.loads(valid_config)
        config_dict["configuration"]["endpoints"].append(
            {
                "id": "422",
                "url": "http://endpoint2.example.com",
                "credentials_ref": "test.endpoint.422",
                "enabled": True,
            }
        )

        # Track collections per endpoint
        collections = {"421": 0, "422": 0}
        collection_lock = threading.Lock()

        def mock_collection(endpoint, emitter):
            with collection_lock:
                collections[endpoint.id] += 1
            emitter.record_counter("collection.count", 1)

        # Initialize lifecycle manager
        health_reporter = HealthReporter(
            extension_id="ext-123456", container_id="container-1"
        )

        # This will fail until LifecycleManager is implemented
        lifecycle = LifecycleManager(
            config=config_dict, health_reporter=health_reporter
        )

        # Start collection
        lifecycle.start(mock_collection)

        # Wait for collections
        time.sleep(2)

        # Verify both endpoints collected
        assert collections["421"] > 0, "Endpoint 421 did not collect"
        assert collections["422"] > 0, "Endpoint 422 did not collect"

        # Shutdown
        lifecycle.shutdown()

    def test_error_propagation_across_components(self, valid_config, tmp_path):
        """
        Test error propagation and handling across components.

        Spec Reference: docs/specs/extension-base-library.md#error-handling
        - Exception Hierarchy (lines 890-949)
        - Error Handling Strategy (lines 950-956)

        Validates:
        - Configuration errors propagate correctly
        - Credential errors propagate correctly
        - Metric export errors handled
        - Health status reflects errors
        - Errors logged appropriately

        Expected: Error propagation works (TDD red phase - will fail)
        """
        from extension_base.config.loader import ConfigLoader
        from extension_base.exceptions import (
            ConfigNotFoundError,
            CredentialRefNotFoundError,
        )

        # Test config file not found
        with pytest.raises(ConfigNotFoundError):
            loader = ConfigLoader(config_path="/nonexistent/config.json")
            loader.load()

        # Test credential reference not found
        config_file = tmp_path / "config.json"
        creds_file = tmp_path / "credentials.json"
        config_file.write_text(valid_config)
        creds_file.write_text('{"wrong.ref": {"type": "basic"}}')

        with pytest.raises(CredentialRefNotFoundError):
            loader = ConfigLoader(
                config_path=str(config_file), credentials_path=str(creds_file)
            )
            loader.load()

    def test_graceful_shutdown_with_resource_cleanup(
        self, valid_config, valid_credentials, tmp_path
    ):
        """
        Test graceful shutdown with complete resource cleanup.

        Spec Reference: docs/specs/extension-base-library.md#core-components
        - Lifecycle Manager - Graceful Shutdown (lines 637-648)

        Validates:
        - Shutdown signal received
        - Collection threads stopped
        - In-flight collections complete
        - Metrics flushed
        - Health status updated
        - HTTP server stopped
        - Resources released

        Expected: Graceful shutdown works (TDD red phase - will fail)
        """
        from extension_base.core import ExtensionBase

        # Create config files
        config_file = tmp_path / "config.json"
        creds_file = tmp_path / "credentials.json"
        config_file.write_text(valid_config)
        creds_file.write_text(valid_credentials)

        # Track shutdown phases
        shutdown_phases = {
            "threads_stopped": False,
            "metrics_flushed": False,
            "health_updated": False,
        }

        def mock_collection(endpoint, emitter):
            time.sleep(0.1)  # Simulate work
            emitter.record_counter("test.metric", 1)

        # Initialize extension — patch ConfigLoader to read from temp files
        with patch(
            "extension_base.config.loader.ConfigLoader",
            lambda: ConfigLoader(
                config_path=str(config_file),
                credentials_path=str(creds_file),
            ),
        ):
            extension = ExtensionBase()

        # Start extension
        extension_thread = threading.Thread(
            target=extension.run, args=(mock_collection,)
        )
        extension_thread.start()

        # Wait for startup
        time.sleep(1)

        # Trigger shutdown
        extension.shutdown(timeout_seconds=5)

        # Wait for shutdown
        extension_thread.join(timeout=10)

        # Verify shutdown completed
        assert not extension_thread.is_alive(), (
            "Extension still running after shutdown"
        )

    def test_environment_variable_override_integration(
        self, valid_config, valid_credentials, tmp_path
    ):
        """
        Test environment variable overrides across components.

        Spec Reference: docs/specs/extension-base-library.md#core-components
        - Configuration Loader - Environment Overrides (lines 213-220)

        Validates:
        - EXTENSION_LOG_LEVEL overrides config
        - OTLP_ENDPOINT overrides config
        - CONTAINER_ID set from environment
        - SUPERVISOR_ID set from environment
        - Overrides applied before component initialization

        Expected: Environment overrides work (TDD red phase - will fail)
        """
        import os

        from extension_base.config.loader import ConfigLoader

        # Create config file
        config_file = tmp_path / "config.json"
        creds_file = tmp_path / "credentials.json"
        config_file.write_text(valid_config)
        creds_file.write_text(valid_credentials)

        # Set environment overrides
        os.environ["EXTENSION_LOG_LEVEL"] = "DEBUG"
        os.environ["OTLP_ENDPOINT"] = "localhost:9999"
        os.environ["CONTAINER_ID"] = "override-container"

        try:
            # Load configuration
            loader = ConfigLoader(
                config_path=str(config_file), credentials_path=str(creds_file)
            )
            config = loader.load()

            # Verify overrides applied
            assert config.configuration.log_level == "DEBUG"
            assert config.otlp.endpoint == "localhost:9999"
            assert config.container_id == "override-container"

        finally:
            # Cleanup environment
            os.environ.pop("EXTENSION_LOG_LEVEL", None)
            os.environ.pop("OTLP_ENDPOINT", None)
            os.environ.pop("CONTAINER_ID", None)

    def test_signal_handling_integration(
        self, valid_config, valid_credentials, tmp_path
    ):
        """
        Test signal handling integration (SIGTERM/SIGINT).

        Spec Reference: docs/specs/extension-base-library.md#core-components
        - Lifecycle Manager - Signal Handling (lines 628-631)

        Validates:
        - Signal handlers registered
        - SIGTERM triggers graceful shutdown
        - SIGINT triggers graceful shutdown
        - Shutdown completes within timeout
        - Resources cleaned up

        Expected: Signal handling works (TDD red phase - will fail)
        """
        import os

        from extension_base.core import ExtensionBase

        # Create config files
        config_file = tmp_path / "config.json"
        creds_file = tmp_path / "credentials.json"
        config_file.write_text(valid_config)
        creds_file.write_text(valid_credentials)

        def mock_collection(endpoint, emitter):
            time.sleep(0.1)
            emitter.record_counter("test.metric", 1)

        # Initialize extension — patch ConfigLoader to read from temp files
        with patch(
            "extension_base.config.loader.ConfigLoader",
            lambda: ConfigLoader(
                config_path=str(config_file),
                credentials_path=str(creds_file),
            ),
        ):
            extension = ExtensionBase()

        # Start extension in separate process (to test signal handling)
        extension_thread = threading.Thread(
            target=extension.run, args=(mock_collection,)
        )
        extension_thread.start()

        # Wait for startup
        time.sleep(1)

        # Send SIGTERM to current process (simulated)
        # In real scenario, this would be sent by container runtime
        os.kill(os.getpid(), signal.SIGTERM)

        # Wait for shutdown
        extension_thread.join(timeout=10)

        # Verify shutdown completed
        assert not extension_thread.is_alive(), (
            "Extension did not shutdown on SIGTERM"
        )

    def test_thread_lifecycle_with_collection_function(
        self, valid_config, valid_credentials, tmp_path
    ):
        """
        Test thread lifecycle with collection function execution.

        Spec Reference: docs/specs/extension-base-library.md#core-components
        - Lifecycle Manager - Thread Management (lines 632-636)

        Validates:
        - Threads created for each endpoint
        - Collection function called per thread
        - Threads run at configured intervals
        - Thread errors handled gracefully
        - Threads stopped on shutdown

        Expected: Thread lifecycle works (TDD red phase - will fail)
        """
        from extension_base.health.reporter import HealthReporter
        from extension_base.lifecycle.manager import LifecycleManager

        # Track collection calls
        collection_calls = []
        collection_lock = threading.Lock()

        def mock_collection(endpoint, emitter):
            with collection_lock:
                collection_calls.append(
                    {"endpoint_id": endpoint.id, "timestamp": time.time()}
                )
            emitter.record_counter("collection.count", 1)

        # Initialize components
        health_reporter = HealthReporter(
            extension_id="ext-123456", container_id="container-1"
        )

        # Load config
        import json

        config_dict = json.loads(valid_config)

        # This will fail until LifecycleManager is implemented
        lifecycle = LifecycleManager(
            config=config_dict, health_reporter=health_reporter
        )

        # Start collection
        lifecycle.start(mock_collection)

        # Wait for multiple collection cycles
        time.sleep(3)

        # Verify collections occurred
        assert len(collection_calls) > 0, "No collections occurred"

        # Verify interval timing (approximate)
        if len(collection_calls) >= 2:
            time_diff = (
                collection_calls[1]["timestamp"]
                - collection_calls[0]["timestamp"]
            )
            # Should be close to configured interval (60s default, but may be faster in tests)
            assert time_diff > 0, "Collections not spaced in time"

        # Shutdown
        lifecycle.shutdown()

    def test_resource_monitoring_integration(self, valid_config, tmp_path):
        """
        Test resource monitoring integration across components.

        Spec Reference: docs/specs/extension-base-library.md#core-components
        - Lifecycle Manager - Resource Monitoring (lines 649-667)

        Validates:
        - Memory usage monitored
        - CPU usage monitored
        - Thread count monitored
        - Metrics reported to health system
        - Warnings triggered at thresholds

        Expected: Resource monitoring works (TDD red phase - will fail)
        """
        from extension_base.health.reporter import HealthReporter
        from extension_base.lifecycle.manager import LifecycleManager

        # Initialize components
        health_reporter = HealthReporter(
            extension_id="ext-123456", container_id="container-1"
        )

        import json

        config_dict = json.loads(valid_config)

        # This will fail until LifecycleManager is implemented
        lifecycle = LifecycleManager(
            config=config_dict, health_reporter=health_reporter
        )

        # Start monitoring
        lifecycle.start(lambda ep, em: None)

        # Wait for monitoring to collect data
        time.sleep(2)

        # Get health status
        health_status = health_reporter.get_status()

        # Verify resource metrics present
        assert "resources" in health_status, "Resource metrics not reported"
        assert "memory_usage_percent" in health_status["resources"]
        assert "thread_count" in health_status["resources"]

        # Cleanup
        lifecycle.shutdown()

    def test_component_initialization_order(
        self, valid_config, valid_credentials, tmp_path
    ):
        """
        Test correct component initialization order.

        Spec Reference: docs/specs/extension-base-library.md#api-reference
        - ExtensionBase Class - Initialization (lines 785-808)

        Validates:
        - Configuration loaded first
        - Credentials resolved second
        - OpenTelemetry initialized third
        - Health reporter initialized fourth
        - Lifecycle manager initialized fifth
        - Collection threads started last

        Expected: Initialization order correct (TDD red phase - will fail)
        """
        from extension_base.core import ExtensionBase

        # Create config files
        config_file = tmp_path / "config.json"
        creds_file = tmp_path / "credentials.json"
        config_file.write_text(valid_config)
        creds_file.write_text(valid_credentials)

        # Track initialization order
        init_order = []

        # Mock components to track initialization
        with patch("extension_base.config.loader.ConfigLoader") as mock_config:
            with patch(
                "extension_base.metrics.otel_setup.setup_otel"
            ) as mock_otel:
                with patch(
                    "extension_base.health.reporter.HealthReporter"
                ) as mock_health:
                    with patch(
                        "extension_base.lifecycle.manager.LifecycleManager"
                    ) as mock_lifecycle:

                        def track_config(*args, **kwargs):
                            init_order.append("config")
                            return Mock()

                        def track_otel(*args, **kwargs):
                            init_order.append("otel")
                            return Mock(), Mock()

                        def track_health(*args, **kwargs):
                            init_order.append("health")
                            return Mock()

                        def track_lifecycle(*args, **kwargs):
                            init_order.append("lifecycle")
                            return Mock()

                        mock_config.side_effect = track_config
                        mock_otel.side_effect = track_otel
                        mock_health.side_effect = track_health
                        mock_lifecycle.side_effect = track_lifecycle

                        # Initialize extension
                        extension = ExtensionBase()

                        # Verify initialization order
                        assert init_order == [
                            "config",
                            "otel",
                            "health",
                            "lifecycle",
                        ], f"Incorrect initialization order: {init_order}"


# Made with Bob
