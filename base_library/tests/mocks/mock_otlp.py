# (c) Copyright IBM Corp. 2026
"""
Mock OTLP server for testing metrics export.

Provides a simulated OTLP endpoint that can:
- Accept metric export requests
- Track exported metrics via the OTel SDK in-memory reader
- Simulate export failures
- Validate metric format and attributes
"""

from typing import Any
from unittest.mock import MagicMock

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource


class MockOTLPServer:
    """
    Mock OTLP server for testing metric export functionality.

    Uses the OTel SDK's InMemoryMetricReader internally so the real
    MeterProvider pipeline can be exercised without a network endpoint.
    The ``meter_provider`` attribute is a fully configured MeterProvider
    that tests should use instead of calling ``setup_otel()``.

    Attributes:
        endpoint: Nominal endpoint string (kept for API compatibility).
        should_fail: Whether to simulate export failures.
        failure_reason: Error message for simulated failures.
    """

    def __init__(
        self,
        endpoint: str = "localhost:4317",
        should_fail: bool = False,
        failure_reason: str | None = None,
    ):
        self.endpoint = endpoint
        self.should_fail = should_fail
        self.failure_reason = failure_reason or "Mock export failure"
        self._is_running = False

        # In-memory reader — collect() pulls metrics without a network call
        self._reader = InMemoryMetricReader()
        resource = Resource.create({"service.name": "mock-otlp-server"})
        self.meter_provider = MeterProvider(
            resource=resource, metric_readers=[self._reader]
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the mock server."""
        self._is_running = True

    def stop(self) -> None:
        """Stop the mock server and shut down the MeterProvider."""
        self._is_running = False
        try:
            self.meter_provider.shutdown()
        except Exception:
            pass

    def is_running(self) -> bool:
        """Check if server is running."""
        return self._is_running

    # ------------------------------------------------------------------
    # Metrics introspection
    # ------------------------------------------------------------------

    def _collect(self):
        """Return the current MetricsData snapshot from the in-memory reader."""
        return self._reader.get_metrics_data()

    def _all_metrics(self) -> list[Any]:
        """Flatten all Metric objects from the current snapshot."""
        data = self._collect()
        return [
            metric
            for rm in data.resource_metrics
            for sm in rm.scope_metrics
            for metric in sm.metrics
        ]

    @property
    def metrics_received(self) -> int:
        """Number of distinct metric instruments collected so far."""
        return len(self._all_metrics())

    def get_export_count(self) -> int:
        """Number of distinct metric instruments collected (alias for metrics_received)."""
        return self.metrics_received

    def get_exported_metrics(self) -> list[dict[str, Any]]:
        """Return collected metrics as a list of ``{"name": ..., "data": ...}`` dicts."""
        return [
            {"name": m.name, "data": m.data}
            for m in self._all_metrics()
        ]

    def get_metrics_by_name(self, name: str) -> list[Any]:
        """Return Metric objects whose name matches *name*."""
        return [m for m in self._all_metrics() if m.name == name]

    def clear_metrics(self) -> None:
        """Reset the in-memory reader by replacing it with a fresh one."""
        self._reader = InMemoryMetricReader()
        resource = Resource.create({"service.name": "mock-otlp-server"})
        self.meter_provider = MeterProvider(
            resource=resource, metric_readers=[self._reader]
        )

    def set_failure_mode(
        self, should_fail: bool, reason: str | None = None
    ) -> None:
        """Configure failure simulation (for API compatibility)."""
        self.should_fail = should_fail
        if reason:
            self.failure_reason = reason

    def verify_metric_exported(
        self, name: str, attributes: dict[str, str] | None = None
    ) -> bool:
        """
        Verify a metric with *name* was collected.

        Args:
            name: Metric name to look for.
            attributes: If supplied, checks that at least one data point
                carries all the specified attributes.

        Returns:
            True if a matching metric (and optionally attributes) was found.
        """
        metrics = self.get_metrics_by_name(name)
        if not metrics:
            return False
        if attributes is None:
            return True

        for metric in metrics:
            for dp in getattr(metric.data, "data_points", []):
                dp_attrs = dict(getattr(dp, "attributes", {}))
                if all(dp_attrs.get(k) == v for k, v in attributes.items()):
                    return True

        return False


def create_mock_meter_provider() -> MagicMock:
    """
    Create a mock MeterProvider for testing.

    Returns:
        MagicMock configured to simulate MeterProvider behavior
    """
    mock_provider = MagicMock()
    mock_meter = MagicMock()
    mock_provider.get_meter = MagicMock(return_value=mock_meter)
    mock_provider.shutdown = MagicMock(return_value=True)
    mock_provider.force_flush = MagicMock(return_value=True)
    return mock_provider


# Made with Bob
