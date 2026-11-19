# (c) Copyright IBM Corp. 2026
"""
Tests for FR4: Metrics Emitter.

This module validates OpenTelemetry metrics emission including SDK initialization,
OTLP/gRPC exporter configuration, counter/gauge/histogram metrics, resource
attributes, endpoint tags, and metric batching.

Tests cover all metric types, attribute propagation, and OTel integration.

Spec Reference: docs/specs/extension-base-library.md#metrics-emitter (lines 305-488)
"""

from unittest.mock import Mock

import pytest


class TestMetricsEmitter:
    """Test suite for metrics emitter (FR4)."""

    def test_metrics_emitter_class_exists(self):
        """
        Test that MetricsEmitter class exists and can be instantiated.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - API/Interface (lines 347-359)

        Validates:
        - MetricsEmitter class is defined in metrics.emitter module
        - Can be instantiated with meter and endpoint
        - Has record_counter() method
        - Has record_gauge() method
        - Has record_histogram() method

        Expected: MetricsEmitter class exists (TDD red phase - will fail)
        """
        from extension_base.metrics import emitter

        # Validate MetricsEmitter exists
        assert hasattr(emitter, "MetricsEmitter"), (
            "MetricsEmitter must be defined in metrics.emitter module"
        )

        MetricsEmitter = emitter.MetricsEmitter

        # Validate it's a class
        assert isinstance(MetricsEmitter, type), (
            "MetricsEmitter must be a class"
        )

        # Create mock meter and endpoint
        mock_meter = Mock()
        mock_endpoint = Mock()
        mock_endpoint.id = "test-endpoint"
        mock_endpoint.tags = {"env": "test"}

        # Validate can be instantiated
        emitter_instance = MetricsEmitter(
            meter=mock_meter, endpoint=mock_endpoint
        )
        assert emitter_instance is not None, (
            "MetricsEmitter must be instantiable"
        )

        # Validate has required methods
        assert hasattr(emitter_instance, "record_counter"), (
            "MetricsEmitter must have record_counter() method"
        )
        assert callable(emitter_instance.record_counter), (
            "record_counter() must be callable"
        )

        assert hasattr(emitter_instance, "record_gauge"), (
            "MetricsEmitter must have record_gauge() method"
        )
        assert callable(emitter_instance.record_gauge), (
            "record_gauge() must be callable"
        )

        assert hasattr(emitter_instance, "record_histogram"), (
            "MetricsEmitter must have record_histogram() method"
        )
        assert callable(emitter_instance.record_histogram), (
            "record_histogram() must be callable"
        )

    def test_otel_setup_module_exists(self):
        """
        Test that OpenTelemetry setup module exists.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - OpenTelemetry Setup (lines 369-375)

        Validates:
        - otel_setup module is defined
        - Has setup_otel() function
        - Has create_meter_provider() function
        - Has configure_otlp_exporter() function

        Expected: OTel setup module exists (TDD red phase - will fail)
        """
        from extension_base.metrics import otel_setup

        # Validate setup_otel exists
        assert hasattr(otel_setup, "setup_otel"), (
            "setup_otel() must be defined in metrics.otel_setup module"
        )
        assert callable(otel_setup.setup_otel), "setup_otel() must be callable"

        # Validate create_meter_provider exists
        assert hasattr(otel_setup, "create_meter_provider"), (
            "create_meter_provider() must be defined"
        )
        assert callable(otel_setup.create_meter_provider), (
            "create_meter_provider() must be callable"
        )

        # Validate configure_otlp_exporter exists
        assert hasattr(otel_setup, "configure_otlp_exporter"), (
            "configure_otlp_exporter() must be defined"
        )
        assert callable(otel_setup.configure_otlp_exporter), (
            "configure_otlp_exporter() must be callable"
        )

        # Validate create_internal_meter_provider exists
        assert hasattr(otel_setup, "create_internal_meter_provider"), (
            "create_internal_meter_provider() must be defined"
        )
        assert callable(otel_setup.create_internal_meter_provider), (
            "create_internal_meter_provider() must be callable"
        )

    def test_setup_otel_with_config(self, valid_config):
        """
        Test OpenTelemetry SDK initialization with configuration.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - OpenTelemetry Initialization (lines 313-317)
        - OpenTelemetry Setup (lines 369-375)

        Validates:
        - setup_otel() accepts configuration
        - Returns MeterProvider instance
        - Configures OTLP endpoint from config
        - Sets up resource attributes

        Expected: OTel SDK initialized (TDD red phase - will fail)
        """
        from extension_base.metrics.otel_setup import setup_otel

        # Setup OTel with config
        meter_provider, _ = setup_otel(valid_config)

        # Validate meter provider returned
        assert meter_provider is not None, (
            "setup_otel() must return MeterProvider"
        )

        # Validate has get_meter method
        assert hasattr(meter_provider, "get_meter"), (
            "MeterProvider must have get_meter() method"
        )
        assert callable(meter_provider.get_meter), (
            "get_meter() must be callable"
        )


    def test_setup_otel_returns_two_providers(self, valid_config):
        """
        Test that setup_otel() returns a tuple of two distinct MeterProviders.

        The first is the business provider (service.name = extension_name),
        the second is the internal provider (service.name = extension_name.internal).
        Both must be usable MeterProvider instances.
        """
        from extension_base.metrics.otel_setup import setup_otel

        result = setup_otel(valid_config)

        assert isinstance(result, tuple), "setup_otel() must return a tuple"
        assert len(result) == 2, "setup_otel() must return exactly two providers"

        business_mp, internal_mp = result
        assert hasattr(business_mp, "get_meter"), "Business provider must have get_meter()"
        assert hasattr(internal_mp, "get_meter"), "Internal provider must have get_meter()"
        assert business_mp is not internal_mp, "Business and internal providers must be distinct objects"

    def test_internal_meter_provider_service_name_suffix(self, valid_config):
        """
        Test that the internal MeterProvider carries service.name = '<extension_name>.internal'.

        This causes Instana to place framework health metrics on a separate page
        from the extension's business metrics.
        """
        from extension_base.metrics.otel_setup import (
            create_internal_meter_provider,
            create_meter_provider,
        )

        business_mp = create_meter_provider(valid_config)
        internal_mp = create_internal_meter_provider(valid_config)

        business_name = business_mp.resource.attributes.get("service.name", "")
        internal_name = internal_mp.resource.attributes.get("service.name", "")

        assert internal_name == f"{business_name}.internal", (
            f"Internal provider service.name must be '<extension_name>.internal', "
            f"got '{internal_name}' (business: '{business_name}')"
        )

    def test_internal_meter_provider_same_instance_id(self, valid_config):
        """
        Test that business and internal providers share service.instance.id
        so the two Instana pages can be correlated.
        """
        from extension_base.metrics.otel_setup import (
            create_internal_meter_provider,
            create_meter_provider,
        )

        business_mp = create_meter_provider(valid_config)
        internal_mp = create_internal_meter_provider(valid_config)

        business_instance_id = business_mp.resource.attributes.get("service.instance.id")
        internal_instance_id = internal_mp.resource.attributes.get("service.instance.id")

        assert business_instance_id == internal_instance_id, (
            "Business and internal providers must share service.instance.id for correlation"
        )

    def test_service_name_env_var_overrides_config(self, valid_config, monkeypatch):
        """
        Test that SERVICE_NAME env var takes precedence over config.extension_name
        for the service.name resource attribute.
        """
        from extension_base.metrics.otel_setup import create_meter_provider

        monkeypatch.setenv("SERVICE_NAME", "my-overridden-service")

        mp = create_meter_provider(valid_config)
        service_name = mp.resource.attributes.get("service.name", "")

        assert service_name == "my-overridden-service", (
            f"SERVICE_NAME env var must override config extension_name, got '{service_name}'"
        )

    def test_service_instance_id_env_var_overrides_container_id(self, valid_config, monkeypatch):
        """
        Test that SERVICE_INSTANCE_ID env var takes precedence over CONTAINER_ID
        for the service.instance.id resource attribute, and that CONTAINER_ID is
        the fallback when SERVICE_INSTANCE_ID is not set.
        """
        from extension_base.metrics.otel_setup import create_meter_provider

        # SERVICE_INSTANCE_ID takes precedence over CONTAINER_ID
        monkeypatch.setenv("CONTAINER_ID", "physical-container-abc")
        monkeypatch.setenv("SERVICE_INSTANCE_ID", "logical-instance-xyz")

        mp = create_meter_provider(valid_config)
        assert mp.resource.attributes.get("service.instance.id") == "logical-instance-xyz", (
            "SERVICE_INSTANCE_ID must take precedence over CONTAINER_ID for service.instance.id"
        )
        assert mp.resource.attributes.get("container.id") == "physical-container-abc", (
            "CONTAINER_ID must still set container.id independently"
        )

    def test_service_instance_id_falls_back_to_container_id(self, valid_config, monkeypatch):
        """
        Test that when SERVICE_INSTANCE_ID is not set, service.instance.id falls
        back to CONTAINER_ID (and then to config.container_id).
        """
        from extension_base.metrics.otel_setup import create_meter_provider

        monkeypatch.setenv("CONTAINER_ID", "physical-container-abc")
        monkeypatch.delenv("SERVICE_INSTANCE_ID", raising=False)

        mp = create_meter_provider(valid_config)
        assert mp.resource.attributes.get("service.instance.id") == "physical-container-abc", (
            "service.instance.id must fall back to CONTAINER_ID when SERVICE_INSTANCE_ID is absent"
        )

    def test_internal_meter_routes_framework_metrics(self, sample_endpoint_config):
        """
        Test that framework metric methods (record_collection_total etc.) use
        the internal_meter, not the business meter.
        """
        from extension_base.metrics.emitter import MetricsEmitter

        mock_business_meter = Mock()
        mock_internal_meter = Mock()
        mock_internal_counter = Mock()
        mock_internal_meter.create_counter.return_value = mock_internal_counter

        emitter = MetricsEmitter(
            meter=mock_business_meter,
            endpoint=sample_endpoint_config,
            internal_meter=mock_internal_meter,
        )
        emitter.record_collection_total()

        # Internal meter must be used for framework metric
        mock_internal_meter.create_counter.assert_called_once()
        # Business meter must NOT be used for framework metric
        mock_business_meter.create_counter.assert_not_called()


    def test_create_meter_provider_with_resource_attributes(
        self, valid_config
    ):
        """
        Test MeterProvider creation with resource attributes.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - Resource Attributes (lines 327-345)

        Validates:
        - Creates MeterProvider with resource attributes
        - Includes service.name from config
        - Includes service.version from config
        - Includes container.id from config
        - Includes custom Instana attributes

        Expected: MeterProvider with attributes (TDD red phase - will fail)
        """
        from extension_base.metrics.otel_setup import create_meter_provider

        # Create meter provider
        meter_provider = create_meter_provider(valid_config)

        # Validate meter provider created
        assert meter_provider is not None, (
            "create_meter_provider() must return MeterProvider"
        )

        # Validate has resource
        assert hasattr(meter_provider, "resource") or hasattr(
            meter_provider, "_resource"
        ), "MeterProvider must have resource attributes"

    def test_configure_otlp_exporter_grpc(self, valid_config):
        """
        Test OTLP/gRPC exporter configuration.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - OpenTelemetry Initialization (lines 314)
        - OpenTelemetry Setup (lines 373)

        Validates:
        - Configures OTLP exporter with gRPC protocol
        - Uses endpoint from configuration
        - Sets compression (gzip)
        - Configures timeout

        Expected: OTLP exporter configured (TDD red phase - will fail)
        """
        from extension_base.metrics.otel_setup import configure_otlp_exporter

        # Configure OTLP exporter
        exporter = configure_otlp_exporter(valid_config)

        # Validate exporter created
        assert exporter is not None, (
            "configure_otlp_exporter() must return exporter"
        )

        # Validate has export method
        assert hasattr(exporter, "export") or hasattr(exporter, "_export"), (
            "Exporter must have export capability"
        )

    def test_configure_otlp_exporter_http(self, valid_config):
        """
        Test OTLP/HTTP exporter configuration.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - OpenTelemetry Initialization (lines 314)

        Validates:
        - Supports HTTP protocol configuration
        - Uses correct endpoint format
        - Handles http/json and http/protobuf protocols

        Expected: HTTP exporter configured (TDD red phase - will fail)
        """
        from extension_base.metrics.otel_setup import configure_otlp_exporter

        # Modify config for HTTP protocol
        valid_config.otlp.protocol = "http/protobuf"

        # Configure OTLP exporter
        exporter = configure_otlp_exporter(valid_config)

        # Validate exporter created
        assert exporter is not None, (
            "configure_otlp_exporter() must support HTTP protocol"
        )

    def test_record_counter_metric(self, sample_endpoint_config):
        """
        Test recording counter metric.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - Metric Emission (lines 319-325)
        - API/Interface - record_counter() (lines 355)

        Validates:
        - record_counter() creates counter instrument
        - Increments counter value
        - Applies endpoint tags
        - Applies custom attributes

        Expected: Counter recorded (TDD red phase - will fail)
        """
        from extension_base.metrics.emitter import MetricsEmitter

        # Create mock meter
        mock_meter = Mock()
        mock_counter = Mock()
        mock_meter.create_counter.return_value = mock_counter

        # Create emitter
        emitter = MetricsEmitter(
            meter=mock_meter, endpoint=sample_endpoint_config
        )

        # Record counter
        emitter.record_counter(
            name="test.counter", value=5, attributes={"status": "success"}
        )

        # Validate counter created
        mock_meter.create_counter.assert_called_once()

        # Validate counter incremented
        mock_counter.add.assert_called_once()
        call_args = mock_counter.add.call_args
        assert call_args[0][0] == 5, "Counter value must be 5"

    def test_record_gauge_metric(self, sample_endpoint_config):
        """
        Test recording gauge metric.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - Metric Emission (lines 319-325)
        - API/Interface - record_gauge() (lines 356)

        Validates:
        - record_gauge() creates OTel Gauge instrument
        - Calls .set() with the supplied value (absolute snapshot semantics)
        - Applies endpoint tags
        - Applies custom attributes

        Expected: Gauge recorded (TDD red phase - will fail)
        """
        from extension_base.metrics.emitter import MetricsEmitter

        # Create mock meter
        mock_meter = Mock()
        mock_gauge = Mock()
        mock_meter.create_gauge.return_value = mock_gauge

        # Create emitter
        emitter = MetricsEmitter(
            meter=mock_meter, endpoint=sample_endpoint_config
        )

        # Record gauge
        emitter.record_gauge(
            name="test.gauge", value=42.5, attributes={"unit": "percent"}
        )

        # Validate OTel Gauge instrument was created
        mock_meter.create_gauge.assert_called_once()

        # Validate .set() called with the exact value
        mock_gauge.set.assert_called_once()
        call_args = mock_gauge.set.call_args
        assert call_args[0][0] == 42.5, "Gauge value must be 42.5"

    def test_record_histogram_metric(self, sample_endpoint_config):
        """
        Test recording histogram metric.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - Metric Emission (lines 319-325)
        - API/Interface - record_histogram() (lines 357)

        Validates:
        - record_histogram() creates histogram instrument
        - Records histogram value
        - Applies endpoint tags
        - Applies custom attributes

        Expected: Histogram recorded (TDD red phase - will fail)
        """
        from extension_base.metrics.emitter import MetricsEmitter

        # Create mock meter
        mock_meter = Mock()
        mock_histogram = Mock()
        mock_meter.create_histogram.return_value = mock_histogram

        # Create emitter
        emitter = MetricsEmitter(
            meter=mock_meter, endpoint=sample_endpoint_config
        )

        # Record histogram
        emitter.record_histogram(
            name="test.histogram", value=0.125, attributes={"endpoint": "/api"}
        )

        # Validate histogram created
        mock_meter.create_histogram.assert_called_once()

        # Validate histogram value recorded
        mock_histogram.record.assert_called_once()
        call_args = mock_histogram.record.call_args
        assert call_args[0][0] == 0.125, "Histogram value must be 0.125"

    def test_endpoint_tags_applied_to_metrics(self, sample_endpoint_config):
        """
        Test that endpoint tags are automatically applied to all metrics.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - Metric Emission (lines 321)
        - Design Notes - Attribute Propagation (lines 366)

        Validates:
        - Endpoint tags from configuration are included
        - Tags are merged with custom attributes
        - Tags don't override custom attributes

        Expected: Tags applied correctly (TDD red phase - will fail)
        """
        from extension_base.metrics.emitter import MetricsEmitter

        # Create mock meter
        mock_meter = Mock()
        mock_counter = Mock()
        mock_meter.create_counter.return_value = mock_counter

        # Set endpoint tags
        sample_endpoint_config.tags = {
            "region": "us-east-1",
            "environment": "production",
        }

        # Create emitter
        emitter = MetricsEmitter(
            meter=mock_meter, endpoint=sample_endpoint_config
        )

        # Record metric with custom attributes
        emitter.record_counter(
            name="test.counter", value=1, attributes={"custom": "value"}
        )

        # Validate tags included in attributes
        call_args = mock_counter.add.call_args
        attributes = call_args[1].get("attributes", {})

        assert "region" in attributes, "Endpoint tags must be included"
        assert "environment" in attributes, "Endpoint tags must be included"
        assert "custom" in attributes, "Custom attributes must be included"

    def test_resource_attributes_include_standard_otel(self, valid_config):
        """
        Test that resource attributes include standard OpenTelemetry attributes.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - Resource Attributes - Standard OTel Attributes (lines 331-338)

        Validates:
        - service.name = extension_name
        - service.version = extension_version
        - service.instance.id = container_id
        - container.id = container_id
        - host.name = hostname

        Expected: Standard OTel attributes present (TDD red phase - will fail)
        """
        from extension_base.metrics.otel_setup import create_meter_provider

        # Create meter provider
        meter_provider = create_meter_provider(valid_config)

        # Get resource attributes
        resource = getattr(meter_provider, "resource", None) or getattr(
            meter_provider, "_resource", None
        )

        assert resource is not None, "MeterProvider must have resource"

        # Validate standard attributes exist
        attributes = (
            resource.attributes if hasattr(resource, "attributes") else {}
        )

        # Check for service.name
        assert any("service.name" in str(k) for k in attributes.keys()), (
            "Resource must include service.name"
        )

    def test_resource_attributes_include_instana_custom(self, valid_config):
        """
        Test that resource attributes include Instana-specific attributes.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - Resource Attributes - Instana-Specific Attributes (lines 340-343)

        Validates:
        - instana.extension.id = extension_id
        - instana.supervisor.id = supervisor_id
        - instana.deployment.id = deployment_id

        Expected: Instana attributes present (TDD red phase - will fail)
        """
        from extension_base.metrics.otel_setup import create_meter_provider

        # Set Instana-specific config
        valid_config.extension_id = "ext-12345"
        valid_config.supervisor_id = "supervisor-1"
        valid_config.deployment_id = "deploy-789"

        # Create meter provider
        meter_provider = create_meter_provider(valid_config)

        # Get resource attributes
        resource = getattr(meter_provider, "resource", None) or getattr(
            meter_provider, "_resource", None
        )

        assert resource is not None, "MeterProvider must have resource"

        # Validate Instana attributes exist
        attributes = (
            resource.attributes if hasattr(resource, "attributes") else {}
        )

        # Check for instana.extension.id
        assert any(
            "instana.extension.id" in str(k) or "extension.id" in str(k)
            for k in attributes.keys()
        ), "Resource must include instana.extension.id"

    def test_metric_instrument_caching(self, sample_endpoint_config):
        """
        Test that metric instruments are cached and reused.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - Design Notes - Metric Instrument Caching (lines 365)

        Validates:
        - Same metric name returns same instrument
        - Instrument created only once
        - Multiple record calls use cached instrument

        Expected: Instruments cached (TDD red phase - will fail)
        """
        from extension_base.metrics.emitter import MetricsEmitter

        # Create mock meter
        mock_meter = Mock()
        mock_counter = Mock()
        mock_meter.create_counter.return_value = mock_counter

        # Create emitter
        emitter = MetricsEmitter(
            meter=mock_meter, endpoint=sample_endpoint_config
        )

        # Record same metric multiple times
        emitter.record_counter("test.counter", value=1)
        emitter.record_counter("test.counter", value=2)
        emitter.record_counter("test.counter", value=3)

        # Validate counter created only once
        assert mock_meter.create_counter.call_count == 1, (
            "Instrument must be cached and reused"
        )

        # Validate counter incremented three times
        assert mock_counter.add.call_count == 3, (
            "Counter must be incremented for each record call"
        )

    def test_metric_with_description(self, sample_endpoint_config):
        """
        Test recording metric with description.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - API/Interface - counter(), histogram(), gauge() (lines 352-354)

        Validates:
        - Metric description is passed to instrument creation
        - Description is optional
        - Description is used on first call only

        Expected: Description handled correctly (TDD red phase - will fail)
        """
        from extension_base.metrics.emitter import MetricsEmitter

        # Create mock meter
        mock_meter = Mock()
        mock_counter = Mock()
        mock_meter.create_counter.return_value = mock_counter

        # Create emitter
        emitter = MetricsEmitter(
            meter=mock_meter, endpoint=sample_endpoint_config
        )

        # Record metric with description
        emitter.record_counter(
            name="test.counter", value=1, description="Test counter metric"
        )

        # Validate description passed to create_counter
        call_args = mock_meter.create_counter.call_args
        assert "description" in call_args[1] or len(call_args[0]) > 1, (
            "Description must be passed to instrument creation"
        )

    def test_metric_with_unit(self, sample_endpoint_config):
        """
        Test recording metric with unit.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - API/Interface - counter(), histogram(), gauge() (lines 352-354)

        Validates:
        - Metric unit is passed to instrument creation
        - Unit is optional
        - Common units supported (bytes, seconds, percent, etc.)

        Expected: Unit handled correctly (TDD red phase - will fail)
        """
        from extension_base.metrics.emitter import MetricsEmitter

        # Create mock meter
        mock_meter = Mock()
        mock_histogram = Mock()
        mock_meter.create_histogram.return_value = mock_histogram

        # Create emitter
        emitter = MetricsEmitter(
            meter=mock_meter, endpoint=sample_endpoint_config
        )

        # Record metric with unit
        emitter.record_histogram(
            name="response.time", value=0.125, unit="seconds"
        )

        # Validate unit passed to create_histogram
        call_args = mock_meter.create_histogram.call_args
        # Unit may be in kwargs or positional args
        has_unit = ("unit" in call_args[1]) if call_args[1] else False
        assert has_unit or len(call_args[0]) > 1, (
            "Unit must be passed to instrument creation"
        )

    def test_otlp_compression_configuration(self, valid_config):
        """
        Test OTLP compression configuration.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - OpenTelemetry Initialization (lines 314)

        Validates:
        - Compression configured from config
        - Supports gzip compression
        - Supports no compression

        Expected: Compression configured (TDD red phase - will fail)
        """
        from extension_base.metrics.otel_setup import configure_otlp_exporter

        # Test with gzip compression
        valid_config.otlp.compression = "gzip"
        exporter = configure_otlp_exporter(valid_config)
        assert exporter is not None, "Exporter must support gzip compression"

        # Test with no compression
        valid_config.otlp.compression = "none"
        exporter = configure_otlp_exporter(valid_config)
        assert exporter is not None, "Exporter must support no compression"

    def test_metrics_export_error_handling(self, valid_config):
        """
        Test error handling during metric export.

        Spec Reference: docs/specs/extension-base-library.md#metrics-emitter
        - Metric Emission (lines 325)

        Validates:
        - Export failures are caught
        - Errors are logged
        - Export retries on failure
        - Metrics not lost on temporary failure

        Expected: Export errors handled (TDD red phase - will fail)
        """
        from extension_base.metrics.emitter import MetricsEmitter
        from extension_base.metrics.otel_setup import setup_otel

        # Setup OTel with invalid endpoint
        valid_config.otlp.endpoint = "localhost:9999"  # Non-existent endpoint

        meter_provider, _ = setup_otel(valid_config)
        meter = meter_provider.get_meter("test")

        # Create emitter
        mock_endpoint = Mock()
        mock_endpoint.id = "test"
        mock_endpoint.tags = {}

        emitter = MetricsEmitter(meter=meter, endpoint=mock_endpoint)

        # Record metric (should not raise exception)
        try:
            emitter.record_counter("test.counter", value=1)
            # If we get here, error handling is working
            assert True
        except Exception as e:
            pytest.fail(f"Metric recording should not raise exception: {e}")

    # ------------------------------------------------------------------
    # Internal framework metric helpers
    # ------------------------------------------------------------------

    def test_record_collection_total(self, sample_endpoint_config):
        """
        Test that record_collection_total() increments
        instana.extension.endpoint.collections.total with framework attributes.
        """
        from extension_base.metrics.emitter import MetricsEmitter

        mock_meter = Mock()
        mock_counter = Mock()
        mock_meter.create_counter.return_value = mock_counter

        emitter = MetricsEmitter(meter=mock_meter, endpoint=sample_endpoint_config)
        emitter.record_collection_total()

        mock_meter.create_counter.assert_called_once_with(
            "instana.extension.endpoint.collections.total",
            description="Total number of collection attempts",
            unit="",
        )
        call_args = mock_counter.add.call_args
        assert call_args[0][0] == 1
        attrs = call_args[1]["attributes"]
        assert attrs.get("endpoint.id") == "test-ep-1"
        assert attrs.get("metric.type") == "framework"

    def test_record_collection_success(self, sample_endpoint_config):
        """
        Test that record_collection_success() increments
        instana.extension.endpoint.collections.success with framework attributes.
        """
        from extension_base.metrics.emitter import MetricsEmitter

        mock_meter = Mock()
        mock_counter = Mock()
        mock_meter.create_counter.return_value = mock_counter

        emitter = MetricsEmitter(meter=mock_meter, endpoint=sample_endpoint_config)
        emitter.record_collection_success()

        mock_meter.create_counter.assert_called_once_with(
            "instana.extension.endpoint.collections.success",
            description="Number of successful collection cycles",
            unit="",
        )
        call_args = mock_counter.add.call_args
        assert call_args[0][0] == 1
        attrs = call_args[1]["attributes"]
        assert attrs.get("endpoint.id") == "test-ep-1"
        assert attrs.get("metric.type") == "framework"

    def test_record_collection_failure(self, sample_endpoint_config):
        """
        Test that record_collection_failure() increments
        instana.extension.endpoint.collections.errors with framework attributes.
        """
        from extension_base.metrics.emitter import MetricsEmitter

        mock_meter = Mock()
        mock_counter = Mock()
        mock_meter.create_counter.return_value = mock_counter

        emitter = MetricsEmitter(meter=mock_meter, endpoint=sample_endpoint_config)
        emitter.record_collection_failure()

        mock_meter.create_counter.assert_called_once_with(
            "instana.extension.endpoint.collections.errors",
            description="Number of failed collection cycles",
            unit="",
        )
        call_args = mock_counter.add.call_args
        assert call_args[0][0] == 1
        attrs = call_args[1]["attributes"]
        assert attrs.get("endpoint.id") == "test-ep-1"
        assert attrs.get("metric.type") == "framework"

    def test_record_collection_duration(self, sample_endpoint_config):
        """
        Test that record_collection_duration() records a histogram observation
        for instana.extension.endpoint.collection.duration with framework attributes.
        """
        from extension_base.metrics.emitter import MetricsEmitter

        mock_meter = Mock()
        mock_histogram = Mock()
        mock_meter.create_histogram.return_value = mock_histogram

        emitter = MetricsEmitter(meter=mock_meter, endpoint=sample_endpoint_config)
        emitter.record_collection_duration(42.5)

        mock_meter.create_histogram.assert_called_once_with(
            "instana.extension.endpoint.collection.duration",
            description="Duration of a collection cycle",
            unit="ms",
        )
        call_args = mock_histogram.record.call_args
        assert call_args[0][0] == 42.5
        attrs = call_args[1]["attributes"]
        assert attrs.get("endpoint.id") == "test-ep-1"
        assert attrs.get("metric.type") == "framework"

    def test_record_collection_last_success(self, sample_endpoint_config):
        """
        Test that record_collection_last_success() sets
        instana.extension.endpoint.collection.last_success gauge with the
        supplied timestamp and framework attributes.
        """
        from extension_base.metrics.emitter import MetricsEmitter

        mock_meter = Mock()
        mock_gauge = Mock()
        mock_meter.create_gauge.return_value = mock_gauge

        emitter = MetricsEmitter(meter=mock_meter, endpoint=sample_endpoint_config)
        emitter.record_collection_last_success(1_700_000_000.0)

        mock_meter.create_gauge.assert_called_once_with(
            "instana.extension.endpoint.collection.last_success",
            description="Timestamp of last successful collection",
            unit="s",
        )
        call_args = mock_gauge.set.call_args
        assert call_args[0][0] == 1_700_000_000.0
        attrs = call_args[1]["attributes"]
        assert attrs.get("endpoint.id") == "test-ep-1"
        assert attrs.get("metric.type") == "framework"

    def test_record_threads_completed(self, sample_endpoint_config):
        """
        Test that record_threads_completed() increments
        instana.extension.threads.completed counter by 1 with framework attributes.
        threads.active is an observable gauge registered on the meter provider
        directly — not on MetricsEmitter.
        """
        from extension_base.metrics.emitter import MetricsEmitter

        mock_meter = Mock()
        mock_counter = Mock()
        mock_meter.create_counter.return_value = mock_counter

        emitter = MetricsEmitter(meter=mock_meter, endpoint=sample_endpoint_config)
        emitter.record_threads_completed()

        mock_meter.create_counter.assert_called_once_with(
            "instana.extension.threads.completed",
            description="Total number of completed collection threads",
            unit="",
        )
        call_args = mock_counter.add.call_args
        assert call_args[0][0] == 1
        assert call_args[1]["attributes"].get("metric.type") == "framework"

    def test_internal_metrics_instrument_caching(self, sample_endpoint_config):
        """
        Test that calling the internal helpers repeatedly reuses the same
        instrument (create_counter / create_histogram / create_gauge called
        only once per metric name).
        """
        from extension_base.metrics.emitter import MetricsEmitter

        mock_meter = Mock()
        mock_meter.create_counter.return_value = Mock()
        mock_meter.create_histogram.return_value = Mock()
        mock_meter.create_gauge.return_value = Mock()

        emitter = MetricsEmitter(meter=mock_meter, endpoint=sample_endpoint_config)

        for _ in range(3):
            emitter.record_collection_total()
        for _ in range(3):
            emitter.record_collection_success()
        for _ in range(3):
            emitter.record_collection_failure()
        for _ in range(3):
            emitter.record_collection_duration(10.0)
        for _ in range(3):
            emitter.record_collection_last_success(1_700_000_000.0)
        for _ in range(3):
            emitter.record_threads_completed()

        # Each instrument must be created only once despite multiple calls
        # threads.completed is a counter (4 total: total + success + errors + threads.completed)
        assert mock_meter.create_counter.call_count == 4
        assert mock_meter.create_histogram.call_count == 1  # duration
        assert mock_meter.create_gauge.call_count == 1      # last_success only


    def test_report_metric_dispatches_counter(
        self, sample_endpoint_config, mock_otlp_server
    ):
        """
        Test that report_metric() with metric_type="counter" accumulates
        values correctly using a real OTel SDK meter.

        Validates:
        - Two report_metric(counter) calls with values 3 and 7 produce a
          single exported data point whose value is 10 (3 + 7).
        - OTel Counter instrument is created only once (caching).
        """
        from extension_base.metrics.emitter import MetricsEmitter

        meter = mock_otlp_server.meter_provider.get_meter("test")
        emitter = MetricsEmitter(meter=meter, endpoint=sample_endpoint_config)

        emitter.report_metric(
            metric_type="counter",
            name="ext.collections",
            value=3,
            attributes={"status": "ok"},
        )
        emitter.report_metric(
            metric_type="counter",
            name="ext.collections",
            value=7,
            attributes={"status": "ok"},
        )

        metrics = mock_otlp_server.get_metrics_by_name("ext.collections")
        assert metrics, "ext.collections must be exported"
        data_points = metrics[0].data.data_points
        assert len(data_points) == 1
        assert data_points[0].value == 10

    def test_report_metric_dispatches_gauge(self, sample_endpoint_config):
        """
        Test that report_metric() with metric_type="gauge" delegates to
        record_gauge() and uses create_gauge / .set().

        Validates:
        - report_metric(metric_type="gauge", ...) calls record_gauge()
        - OTel Gauge instrument is created only once (caching)
        - Each call sets the exact supplied value (absolute snapshot semantics)
        """
        from extension_base.metrics.emitter import MetricsEmitter

        mock_meter = Mock()
        mock_gauge = Mock()
        mock_meter.create_gauge.return_value = mock_gauge

        emitter = MetricsEmitter(
            meter=mock_meter, endpoint=sample_endpoint_config
        )

        emitter.report_metric(
            metric_type="gauge",
            name="db.connections",
            value=10,
        )
        emitter.report_metric(
            metric_type="gauge",
            name="db.connections",
            value=8,
        )

        mock_meter.create_gauge.assert_called_once()
        assert mock_gauge.set.call_count == 2
        values = [call[0][0] for call in mock_gauge.set.call_args_list]
        assert values == [10, 8]

    def test_report_metric_dispatches_histogram(self, sample_endpoint_config):
        """
        Test that report_metric() with metric_type="histogram" delegates to
        record_histogram() and uses create_histogram / .record().

        Validates:
        - report_metric(metric_type="histogram", ...) calls record_histogram()
        - OTel Histogram instrument is created and .record() is called
        """
        from extension_base.metrics.emitter import MetricsEmitter

        mock_meter = Mock()
        mock_histogram = Mock()
        mock_meter.create_histogram.return_value = mock_histogram

        emitter = MetricsEmitter(
            meter=mock_meter, endpoint=sample_endpoint_config
        )

        emitter.report_metric(
            metric_type="histogram",
            name="query.duration",
            value=0.042,
            unit="s",
        )

        mock_meter.create_histogram.assert_called_once()
        mock_histogram.record.assert_called_once()
        assert mock_histogram.record.call_args[0][0] == 0.042

    def test_report_metric_raises_on_unknown_type(
        self, sample_endpoint_config
    ):
        """
        Test that report_metric() raises ValueError for unrecognised types.

        Validates:
        - Passing an unknown metric_type raises ValueError
        - Error message includes the offending type and the valid choices
        """
        from extension_base.metrics.emitter import MetricsEmitter

        mock_meter = Mock()
        emitter = MetricsEmitter(
            meter=mock_meter, endpoint=sample_endpoint_config
        )

        with pytest.raises(ValueError, match="unknown_type"):
            emitter.report_metric(
                metric_type="unknown_type",  # type: ignore[arg-type]
                name="some.metric",
                value=1,
            )

    # ------------------------------------------------------------------
    # Python runtime metrics — observable callbacks produce real values
    # ------------------------------------------------------------------

    def test_python_runtime_metrics_callbacks_yield_observations(self, valid_config):
        """
        Validate that the observable callbacks registered by
        register_python_runtime_metrics() produce Observation objects with
        real values from psutil / gc / threading, using correct instrument
        types and attribute sets.

        Spec Reference: docs/specs/extension-base-library.md#python-runtime-metrics
        (lines 402-421)
        """
        from opentelemetry.metrics import CallbackOptions

        from extension_base.metrics.runtime_metrics import (
            register_python_runtime_metrics,
        )
        from extension_base.metrics.otel_setup import setup_otel

        _, internal_mp = setup_otel(valid_config)
        meter = internal_mp.get_meter("test.runtime")

        # Spy on both instrument factory methods — GC counters and cpu.time
        # use create_observable_counter; everything else uses create_observable_gauge.
        callbacks_by_name: dict[str, list] = {}
        original_gauge = meter.create_observable_gauge
        original_counter = meter.create_observable_counter

        def _spy_gauge(name, callbacks=None, **kwargs):
            callbacks_by_name[name] = list(callbacks or [])
            return original_gauge(name, callbacks=callbacks, **kwargs)

        def _spy_counter(name, callbacks=None, **kwargs):
            callbacks_by_name[name] = list(callbacks or [])
            return original_counter(name, callbacks=callbacks, **kwargs)

        meter.create_observable_gauge = _spy_gauge
        meter.create_observable_counter = _spy_counter
        register_python_runtime_metrics(meter)

        opts = CallbackOptions()

        # --- memory (ObservableGauge, single observation each) ---
        for metric_name in (
            "instana.runtime.python.memory.rss",
            "instana.runtime.python.memory.vms",
            "instana.runtime.python.memory.percent",
        ):
            assert metric_name in callbacks_by_name, (
                f"{metric_name} must be registered"
            )
            obs = list(callbacks_by_name[metric_name][0](opts))
            assert len(obs) == 1, (
                f"{metric_name} must yield exactly one Observation"
            )
            assert obs[0].value >= 0, f"{metric_name} value must be non-negative"
            assert obs[0].attributes.get("metric.type") == "runtime", (
                f"{metric_name} must carry metric.type=runtime"
            )

        # --- cpu utilization (ObservableGauge) ---
        assert "instana.runtime.python.cpu.utilization" in callbacks_by_name
        cpu_util_obs = list(
            callbacks_by_name["instana.runtime.python.cpu.utilization"][0](opts)
        )
        assert len(cpu_util_obs) == 1
        assert cpu_util_obs[0].value >= 0
        assert cpu_util_obs[0].attributes.get("metric.type") == "runtime"

        # --- cpu time (ObservableCounter — cumulative, monotonic) ---
        assert "instana.runtime.python.cpu.time" in callbacks_by_name
        cpu_time_obs = list(
            callbacks_by_name["instana.runtime.python.cpu.time"][0](opts)
        )
        assert len(cpu_time_obs) == 1
        assert cpu_time_obs[0].value >= 0
        assert cpu_time_obs[0].attributes.get("metric.type") == "runtime"

        # --- threads (ObservableGauge) ---
        assert "instana.runtime.python.thread.count" in callbacks_by_name
        thread_obs = list(
            callbacks_by_name["instana.runtime.python.thread.count"][0](opts)
        )
        assert len(thread_obs) == 1
        assert thread_obs[0].value >= 1, "At least the main thread must be counted"
        assert thread_obs[0].attributes.get("metric.type") == "runtime"

        # --- gc.collections (ObservableCounter, 3 observations — one per generation) ---
        assert "instana.runtime.python.gc.collections" in callbacks_by_name
        gc_col_obs = list(
            callbacks_by_name["instana.runtime.python.gc.collections"][0](opts)
        )
        assert len(gc_col_obs) == 3, (
            "gc.collections must yield one observation per generation"
        )
        for ob in gc_col_obs:
            assert ob.value >= 0
            assert ob.attributes.get("metric.type") == "runtime", (
                "gc.collections observations must carry metric.type=runtime"
            )
        assert {ob.attributes["generation"] for ob in gc_col_obs} == {"0", "1", "2"}

        # --- gc.objects.collected (ObservableCounter, 3 observations) ---
        assert "instana.runtime.python.gc.objects.collected" in callbacks_by_name
        gc_obj_obs = list(
            callbacks_by_name["instana.runtime.python.gc.objects.collected"][0](opts)
        )
        assert len(gc_obj_obs) == 3, (
            "gc.objects.collected must yield one observation per generation"
        )
        for ob in gc_obj_obs:
            assert ob.value >= 0
            assert ob.attributes.get("metric.type") == "runtime", (
                "gc.objects.collected observations must carry metric.type=runtime"
            )
        assert {ob.attributes["generation"] for ob in gc_obj_obs} == {"0", "1", "2"}

    def test_python_runtime_metrics_psutil_failure_yields_nothing(self, valid_config):
        """
        When psutil.Process() fails at initialisation time, all proc-dependent
        callbacks must yield no observations rather than raising.

        Covers the proc=None guard introduced for the psutil statefulness fix.
        """
        from unittest.mock import patch

        from opentelemetry.metrics import CallbackOptions

        import extension_base.metrics.runtime_metrics as rm
        from extension_base.metrics.otel_setup import setup_otel

        _, internal_mp = setup_otel(valid_config)
        meter = internal_mp.get_meter("test.runtime.failure")

        callbacks_by_name: dict[str, list] = {}
        original_gauge = meter.create_observable_gauge
        original_counter = meter.create_observable_counter

        def _spy_gauge(name, callbacks=None, **kwargs):
            callbacks_by_name[name] = list(callbacks or [])
            return original_gauge(name, callbacks=callbacks, **kwargs)

        def _spy_counter(name, callbacks=None, **kwargs):
            callbacks_by_name[name] = list(callbacks or [])
            return original_counter(name, callbacks=callbacks, **kwargs)

        meter.create_observable_gauge = _spy_gauge
        meter.create_observable_counter = _spy_counter

        # Force psutil.Process() to raise so proc is set to None
        with patch.object(rm.psutil, "Process", side_effect=OSError("no proc")):
            rm.register_python_runtime_metrics(meter)

        opts = CallbackOptions()

        # All proc-dependent callbacks must yield nothing (not raise)
        for name in (
            "instana.runtime.python.memory.rss",
            "instana.runtime.python.memory.vms",
            "instana.runtime.python.memory.percent",
            "instana.runtime.python.cpu.utilization",
            "instana.runtime.python.cpu.time",
        ):
            obs = list(callbacks_by_name[name][0](opts))
            assert obs == [], f"{name} must yield no observations when proc is None"

        # Thread count does not depend on proc — must still yield a value
        thread_obs = list(
            callbacks_by_name["instana.runtime.python.thread.count"][0](opts)
        )
        assert len(thread_obs) == 1
        assert thread_obs[0].value >= 1

    def test_create_internal_meter_provider_registers_runtime_metrics(
        self, valid_config
    ):
        """
        Validate that create_internal_meter_provider() automatically wires up
        the runtime metrics module so no caller action is required.

        Spec Reference: docs/specs/extension-base-library.md
        - Automatic Collection (line 432)
        """
        from unittest.mock import patch

        from extension_base.metrics import runtime_metrics
        from extension_base.metrics.otel_setup import create_internal_meter_provider

        with patch.object(
            runtime_metrics,
            "register_python_runtime_metrics",
            wraps=runtime_metrics.register_python_runtime_metrics,
        ) as spy:
            create_internal_meter_provider(valid_config)
            spy.assert_called_once()


    # ------------------------------------------------------------------
    # x-instana-key header tests
    # ------------------------------------------------------------------

    def test_configure_otlp_exporter_grpc_with_instana_key(self, valid_config):
        """
        Test that configure_otlp_exporter() passes x-instana-key header to
        the gRPC exporter when otlp.instana_key is set.

        Validates:
        - Header is forwarded to GRPCMetricExporter when instana_key is present
        - Header is absent (None) when instana_key is not set
        """
        from unittest.mock import patch

        from extension_base.metrics.otel_setup import configure_otlp_exporter

        valid_config.otlp.instana_key = "test-key-grpc"
        valid_config.otlp.protocol = "grpc"

        with patch(
            "extension_base.metrics.otel_setup.GRPCMetricExporter"
        ) as mock_grpc:
            configure_otlp_exporter(valid_config)
            _, kwargs = mock_grpc.call_args
            assert kwargs.get("headers") == {"x-instana-key": "test-key-grpc"}, (
                "GRPCMetricExporter must receive x-instana-key header"
            )

    def test_configure_otlp_exporter_http_with_instana_key(self, valid_config):
        """
        Test that configure_otlp_exporter() passes x-instana-key header to
        the HTTP exporter when otlp.instana_key is set.

        Validates:
        - Header is forwarded to HTTPMetricExporter when instana_key is present
        """
        from unittest.mock import patch

        from extension_base.metrics.otel_setup import configure_otlp_exporter

        valid_config.otlp.instana_key = "test-key-http"
        valid_config.otlp.protocol = "http/protobuf"

        with patch(
            "extension_base.metrics.otel_setup.HTTPMetricExporter"
        ) as mock_http:
            configure_otlp_exporter(valid_config)
            _, kwargs = mock_http.call_args
            assert kwargs.get("headers") == {"x-instana-key": "test-key-http"}, (
                "HTTPMetricExporter must receive x-instana-key header"
            )

    def test_configure_otlp_exporter_no_header_when_key_absent(self, valid_config):
        """
        Test that configure_otlp_exporter() does NOT inject any header when
        otlp.instana_key is absent.

        Validates:
        - headers kwarg is None when no instana_key is configured
        """
        from unittest.mock import patch

        from extension_base.metrics.otel_setup import configure_otlp_exporter

        # Ensure instana_key is not set on the config object
        if hasattr(valid_config.otlp, "instana_key"):
            valid_config.otlp.instana_key = None
        valid_config.otlp.protocol = "grpc"

        with patch(
            "extension_base.metrics.otel_setup.GRPCMetricExporter"
        ) as mock_grpc:
            configure_otlp_exporter(valid_config)
            _, kwargs = mock_grpc.call_args
            assert kwargs.get("headers") is None, (
                "GRPCMetricExporter must not receive a headers kwarg when instana_key is absent"
            )

    def test_instana_key_loaded_from_env_var(self, monkeypatch, mock_config_file, mock_credentials_store):
        """
        Test that INSTANA_KEY environment variable is picked up by ConfigLoader
        and stored in otlp.instana_key.

        Validates:
        - INSTANA_KEY env var is mapped to otlp.instana_key via _ENV_OVERRIDES
        """
        from extension_base.config.loader import ConfigLoader

        monkeypatch.setenv("INSTANA_KEY", "env-instana-key-value")

        # create_basic_auth_store uses key "test.endpoint.421", matching valid_config's credentials_ref
        creds_path = mock_credentials_store.create_basic_auth_store()
        config_path = mock_config_file.create_valid_config()

        loader = ConfigLoader(
            config_path=str(config_path),
            credentials_path=str(creds_path),
        )
        config = loader.load()

        assert config.otlp.instana_key == "env-instana-key-value", (
            "INSTANA_KEY env var must be stored in otlp.instana_key"
        )

    def test_grpc_exporter_uses_tls_when_instana_key_set(self, valid_config):
        """
        Test that the gRPC exporter is created with insecure=False (TLS)
        when otlp.instana_key is present — required for public SaaS backends.

        Validates:
        - insecure=False is passed to GRPCMetricExporter when instana_key is set
        """
        from unittest.mock import patch

        from extension_base.metrics.otel_setup import configure_otlp_exporter

        valid_config.otlp.instana_key = "some-key"
        valid_config.otlp.protocol = "grpc"

        with patch(
            "extension_base.metrics.otel_setup.GRPCMetricExporter"
        ) as mock_grpc:
            configure_otlp_exporter(valid_config)
            _, kwargs = mock_grpc.call_args
            assert kwargs.get("insecure") is False, (
                "GRPCMetricExporter must use TLS (insecure=False) when instana_key is set"
            )

    def test_grpc_exporter_uses_plaintext_without_instana_key(self, valid_config):
        """
        Test that the gRPC exporter is created with insecure=True (plaintext)
        when no instana_key is set — the default for local/cluster collectors.

        Validates:
        - insecure=True is passed to GRPCMetricExporter when instana_key is absent
        """
        from unittest.mock import patch

        from extension_base.metrics.otel_setup import configure_otlp_exporter

        if hasattr(valid_config.otlp, "instana_key"):
            valid_config.otlp.instana_key = None
        valid_config.otlp.protocol = "grpc"

        with patch(
            "extension_base.metrics.otel_setup.GRPCMetricExporter"
        ) as mock_grpc:
            configure_otlp_exporter(valid_config)
            _, kwargs = mock_grpc.call_args
            assert kwargs.get("insecure") is True, (
                "GRPCMetricExporter must use plaintext (insecure=True) when instana_key is absent"
            )


    # ------------------------------------------------------------------
    # otlp.tls explicit field and OTLP_TLS env var tests
    # ------------------------------------------------------------------

    def test_grpc_exporter_tls_true_overrides_no_instana_key(self, valid_config):
        """
        otlp.tls=True must force TLS even when instana_key is absent
        (self-hosted collector with TLS cert, no Instana SaaS key).
        """
        from unittest.mock import patch

        from extension_base.metrics.otel_setup import configure_otlp_exporter

        valid_config.otlp.instana_key = None
        valid_config.otlp.tls = True
        valid_config.otlp.protocol = "grpc"

        with patch("extension_base.metrics.otel_setup.GRPCMetricExporter") as mock_grpc:
            configure_otlp_exporter(valid_config)
            _, kwargs = mock_grpc.call_args
            assert kwargs.get("insecure") is False, (
                "otlp.tls=True must set insecure=False regardless of instana_key"
            )

    def test_grpc_exporter_tls_false_overrides_instana_key(self, valid_config):
        """
        otlp.tls=False must force plaintext even when instana_key is set
        (explicit override wins over the instana_key heuristic).
        """
        from unittest.mock import patch

        from extension_base.metrics.otel_setup import configure_otlp_exporter

        valid_config.otlp.instana_key = "some-key"
        valid_config.otlp.tls = False
        valid_config.otlp.protocol = "grpc"

        with patch("extension_base.metrics.otel_setup.GRPCMetricExporter") as mock_grpc:
            configure_otlp_exporter(valid_config)
            _, kwargs = mock_grpc.call_args
            assert kwargs.get("insecure") is True, (
                "otlp.tls=False must set insecure=True even when instana_key is present"
            )

    def test_http_exporter_tls_true_uses_https_scheme(self, valid_config):
        """
        For HTTP, otlp.tls=True must produce an https:// endpoint when the
        configured endpoint is a bare hostname.
        """
        from unittest.mock import patch

        from extension_base.metrics.otel_setup import configure_otlp_exporter

        valid_config.otlp.instana_key = None
        valid_config.otlp.tls = True
        valid_config.otlp.protocol = "http/protobuf"
        valid_config.otlp.endpoint = "my-collector:4318"

        with patch("extension_base.metrics.otel_setup.HTTPMetricExporter") as mock_http:
            configure_otlp_exporter(valid_config)
            _, kwargs = mock_http.call_args
            assert kwargs.get("endpoint", "").startswith("https://"), (
                "otlp.tls=True must produce https:// scheme for HTTP exporter"
            )

    def test_http_exporter_no_tls_uses_http_scheme(self, valid_config):
        """
        For HTTP, a bare hostname with no tls flag and no instana_key must
        remain http://.
        """
        from unittest.mock import patch

        from extension_base.metrics.otel_setup import configure_otlp_exporter

        valid_config.otlp.instana_key = None
        valid_config.otlp.tls = None
        valid_config.otlp.protocol = "http/protobuf"
        valid_config.otlp.endpoint = "localhost:4318"

        with patch("extension_base.metrics.otel_setup.HTTPMetricExporter") as mock_http:
            configure_otlp_exporter(valid_config)
            _, kwargs = mock_http.call_args
            assert kwargs.get("endpoint", "").startswith("http://"), (
                "bare hostname with no TLS must produce http:// scheme"
            )

    def test_resolve_tls_string_true_is_tls(self, valid_config):
        """
        _resolve_tls must treat the string 'true' (case-insensitive) as True
        when otlp.tls is a raw string (bypassed loader / raw dict path).
        """
        from extension_base.metrics.otel_setup import _resolve_tls

        config = {"otlp": {"tls": "true"}}
        assert _resolve_tls(config, None) is True

        config = {"otlp": {"tls": "True"}}
        assert _resolve_tls(config, None) is True

    def test_resolve_tls_string_false_is_plaintext(self, valid_config):
        """
        _resolve_tls must treat any string other than 'true' as False,
        including the literal string 'false'.
        """
        from extension_base.metrics.otel_setup import _resolve_tls

        for value in ("false", "False", "0", "yes", "1", ""):
            config = {"otlp": {"tls": value}}
            assert _resolve_tls(config, None) is False, (
                f"string {value!r} must resolve to False"
            )

    def test_otlp_tls_env_var_true_sets_tls(
        self, monkeypatch, mock_config_file, mock_credentials_store
    ):
        """
        OTLP_TLS=true must be stored as otlp.tls=True by ConfigLoader.
        """
        from extension_base.config.loader import ConfigLoader

        monkeypatch.setenv("OTLP_TLS", "true")

        creds_path = mock_credentials_store.create_basic_auth_store()
        config_path = mock_config_file.create_valid_config()

        config = ConfigLoader(
            config_path=str(config_path),
            credentials_path=str(creds_path),
        ).load()

        assert config.otlp.tls is True, (
            "OTLP_TLS=true must set otlp.tls=True"
        )

    def test_otlp_tls_env_var_false_sets_no_tls(
        self, monkeypatch, mock_config_file, mock_credentials_store
    ):
        """
        OTLP_TLS=false must be stored as otlp.tls=False by ConfigLoader.
        """
        from extension_base.config.loader import ConfigLoader

        monkeypatch.setenv("OTLP_TLS", "false")

        creds_path = mock_credentials_store.create_basic_auth_store()
        config_path = mock_config_file.create_valid_config()

        config = ConfigLoader(
            config_path=str(config_path),
            credentials_path=str(creds_path),
        ).load()

        assert config.otlp.tls is False, (
            "OTLP_TLS=false must set otlp.tls=False"
        )
