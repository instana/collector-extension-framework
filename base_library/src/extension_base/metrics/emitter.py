# (c) Copyright IBM Corp. 2026
"""
Metrics emitter for Extension Base Library.

Provides MetricsEmitter — a thin, endpoint-aware wrapper around an OTel
Meter that caches instruments and automatically merges endpoint tags into
every metric's attribute set.
"""

import logging
from typing import Any, Literal

__all__ = ["MetricsEmitter"]

MetricType = Literal["counter", "gauge", "histogram"]

logger = logging.getLogger(__name__)


def _get_attr(obj: Any, key: str, default: Any = None) -> Any:
    """Read *key* from a dict or an object attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class MetricsEmitter:
    """Emit OpenTelemetry metrics for a single monitored endpoint.

    Wraps an OTel :class:`~opentelemetry.metrics.Meter` and:
    - Caches created instruments (counters, gauges, histograms) by name so
      the underlying SDK ``create_*`` calls are made only once per name.
    - Automatically merges the endpoint's ``tags`` dict into every metric's
      attribute set (custom attributes take precedence over tag values for
      the same key).

    Args:
        meter: An OTel :class:`~opentelemetry.metrics.Meter` instance for
            **business metrics** emitted by the extension developer.
        endpoint: An :class:`~extension_base.config.models.Endpoint` or any
            object/dict that exposes ``id`` and ``tags`` attributes.
        internal_meter: An OTel :class:`~opentelemetry.metrics.Meter` instance
            backed by the **internal** MeterProvider
            (``service.name=<extension_name>.internal``). Framework health
            metrics (collection counts, durations, etc.) are routed through
            this meter so they appear on a separate Instana page.  When
            *None* the business *meter* is used as fallback — preserving
            backwards-compatible behaviour in tests and simple scripts.
    """

    def __init__(self, meter: Any, endpoint: Any, internal_meter: Any = None) -> None:
        self._meter = meter
        self._internal_meter = internal_meter if internal_meter is not None else meter
        self._endpoint = endpoint
        # Two sets of instrument caches — one per meter — keyed by metric name.
        # Kept separate so the same metric name can exist on both the business
        # and internal meters without cross-contamination.
        self._counters:           dict[str, Any] = {}
        self._gauges:             dict[str, Any] = {}
        self._histograms:         dict[str, Any] = {}
        self._internal_counters:  dict[str, Any] = {}
        self._internal_gauges:    dict[str, Any] = {}
        self._internal_histograms: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _endpoint_tags(self) -> dict[str, str]:
        """Return the endpoint's tag dict (empty dict when absent)."""
        tags = _get_attr(self._endpoint, "tags", {})
        return dict(tags) if tags else {}

    def _merge_attrs(
        self, attributes: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Merge endpoint tags with caller-supplied *attributes*.

        Caller attributes take precedence over tag values when keys collide.
        """
        merged = self._endpoint_tags()
        if attributes:
            merged.update(attributes)
        return merged

    def _select_meter(self, internal: bool) -> Any:
        """Return the internal or business meter based on *internal* flag."""
        return self._internal_meter if internal else self._meter

    def _select_cache(self, cache_type: str, internal: bool) -> dict[str, Any]:
        """Return the instrument cache that matches *meter* and *cache_type*."""
        match cache_type:
            case "counter":
                return self._internal_counters if internal else self._counters
            case "gauge":
                return self._internal_gauges if internal else self._gauges
            case "histogram":
                return self._internal_histograms if internal else self._histograms
            case _:
                raise ValueError(f"Unsupported cache_type: {cache_type!r}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_counter(
        self,
        name: str,
        value: int | float = 1,
        attributes: dict[str, Any] | None = None,
        description: str = "",
        unit: str = "",
        *,
        internal: bool = False,
        merge_endpoint_tags: bool = True,
    ) -> None:
        """Increment a counter metric.

        Args:
            name: Metric name (e.g. ``"extension.collections.total"``).
            value: Amount to add (default 1).
            attributes: Additional attributes merged with endpoint tags.
            description: Human-readable description (used at creation time only).
            unit: Unit string (used at creation time only).
            internal: Route to the internal framework health meter when ``True``.
                      Extension developers should leave this at the default ``False``.
            merge_endpoint_tags: When ``False``, endpoint tags are not merged into
                      the attributes. Use for process-level metrics that must not
                      carry per-endpoint tags.
        """
        cache = self._select_cache("counter", internal)
        if name not in cache:
            cache[name] = self._select_meter(internal).create_counter(
                name, description=description, unit=unit
            )
        attrs = self._merge_attrs(attributes) if merge_endpoint_tags else (attributes or {})
        cache[name].add(value, attributes=attrs)

    def record_gauge(
        self,
        name: str,
        value: int | float = 0,
        attributes: dict[str, Any] | None = None,
        description: str = "",
        unit: str = "",
        *,
        internal: bool = False,
        merge_endpoint_tags: bool = True,
    ) -> None:
        """Set a gauge metric to an absolute snapshot value.

        Args:
            name: Metric name.
            value: Current value to set.
            attributes: Additional attributes merged with endpoint tags.
            description: Human-readable description (used at creation time only).
            unit: Unit string (used at creation time only).
            internal: Route to the internal framework health meter when ``True``.
                      Extension developers should leave this at the default ``False``.
            merge_endpoint_tags: When ``False``, endpoint tags are not merged into
                      the attributes. Use for process-level metrics that must not
                      carry per-endpoint tags.
        """
        cache = self._select_cache("gauge", internal)
        if name not in cache:
            cache[name] = self._select_meter(internal).create_gauge(
                name, description=description, unit=unit
            )
        attrs = self._merge_attrs(attributes) if merge_endpoint_tags else (attributes or {})
        cache[name].set(value, attributes=attrs)

    def record_histogram(
        self,
        name: str,
        value: int | float = 0,
        attributes: dict[str, Any] | None = None,
        description: str = "",
        unit: str = "",
        *,
        internal: bool = False,
        merge_endpoint_tags: bool = True,
    ) -> None:
        """Record a histogram observation.

        Args:
            name: Metric name.
            value: Observed value.
            attributes: Additional attributes merged with endpoint tags.
            description: Human-readable description (used at creation time only).
            unit: Unit string (used at creation time only).
            internal: Route to the internal framework health meter when ``True``.
                      Extension developers should leave this at the default ``False``.
            merge_endpoint_tags: When ``False``, endpoint tags are not merged into
                      the attributes. Use for process-level metrics that must not
                      carry per-endpoint tags.
        """
        cache = self._select_cache("histogram", internal)
        if name not in cache:
            cache[name] = self._select_meter(internal).create_histogram(
                name, description=description, unit=unit
            )
        attrs = self._merge_attrs(attributes) if merge_endpoint_tags else (attributes or {})
        cache[name].record(value, attributes=attrs)

    def report_metric(
        self,
        metric_type: "MetricType",
        name: str,
        value: int | float = 0,
        attributes: dict[str, Any] | None = None,
        description: str = "",
        unit: str = "",
    ) -> None:
        """Record a metric by type name, dispatching to the appropriate method.

        A convenience entry-point for data-driven or config-driven code where
        the metric type is not known at write time.

        Args:
            metric_type: One of ``"counter"``, ``"gauge"``, or ``"histogram"``.
            name: Metric name.
            value: Metric value (semantics depend on *metric_type*).
            attributes: Additional attributes merged with endpoint tags.
            description: Human-readable description (used at creation time only).
            unit: Unit string (used at creation time only).

        Raises:
            ValueError: If *metric_type* is not a recognised type.
        """
        _type_to_recorder: dict[str, Any] = {
            "counter": self.record_counter,
            "gauge": self.record_gauge,
            "histogram": self.record_histogram,
        }
        recorder = _type_to_recorder.get(metric_type)
        if recorder is None:
            raise ValueError(
                f"Unknown metric_type {metric_type!r}. "
                f"Expected one of: {list(_type_to_recorder)}"
            )
        recorder(
            name=name,
            value=value,
            attributes=attributes,
            description=description,
            unit=unit,
        )
    # ------------------------------------------------------------------
    # Internal framework metrics
    # ------------------------------------------------------------------

    def _framework_attrs(self) -> dict[str, str]:
        """Return framework attributes for process-level internal metrics."""
        return {"metric.type": "framework"}

    def _framework_endpoint_attrs(self) -> dict[str, str]:
        """Return framework attributes for per-endpoint internal metrics."""
        return {
            **self._framework_attrs(),
            "endpoint.id": str(_get_attr(self._endpoint, "id", "")),
        }

    def record_threads_completed(self) -> None:
        """Increment ``instana.extension.threads.completed`` counter by 1.

        Called once by the lifecycle manager when a collection thread exits,
        regardless of whether it exited cleanly or due to an error.
        Emitted on the internal framework health page.
        """
        self.record_counter(
            name="instana.extension.threads.completed",
            value=1,
            attributes=self._framework_attrs(),
            description="Total number of completed collection threads",
            internal=True,
            merge_endpoint_tags=False,
        )

    def record_collection_total(self) -> None:
        """Increment ``instana.extension.endpoint.collections.total`` counter.

        Called by the lifecycle manager on every collection attempt (before the
        outcome is known), so the total reflects attempts rather than results.
        Emitted on the internal framework health page.
        """
        self.record_counter(
            name="instana.extension.endpoint.collections.total",
            value=1,
            attributes=self._framework_endpoint_attrs(),
            description="Total number of collection attempts",
            internal=True,
        )

    def record_collection_success(self) -> None:
        """Increment ``instana.extension.endpoint.collections.success`` counter.

        Called by the lifecycle manager after each successful collection cycle.
        Emitted on the internal framework health page.
        """
        self.record_counter(
            name="instana.extension.endpoint.collections.success",
            value=1,
            attributes=self._framework_endpoint_attrs(),
            description="Number of successful collection cycles",
            internal=True,
        )

    def record_collection_failure(self) -> None:
        """Increment ``instana.extension.endpoint.collections.errors`` counter.

        Called by the lifecycle manager after each failed collection cycle.
        Emitted on the internal framework health page.
        """
        self.record_counter(
            name="instana.extension.endpoint.collections.errors",
            value=1,
            attributes=self._framework_endpoint_attrs(),
            description="Number of failed collection cycles",
            internal=True,
        )

    def record_collection_duration(self, duration_ms: float) -> None:
        """Record the duration of one collection cycle.

        Records the value under ``instana.extension.endpoint.collection.duration``
        (histogram, unit ``ms``). Called by the lifecycle manager with the
        wall-clock time of the ``collection_func`` call.
        Emitted on the internal framework health page.

        Args:
            duration_ms: Elapsed time of the collection call in milliseconds.
        """
        self.record_histogram(
            name="instana.extension.endpoint.collection.duration",
            value=duration_ms,
            attributes=self._framework_endpoint_attrs(),
            description="Duration of a collection cycle",
            unit="ms",
            internal=True,
        )

    def record_collection_last_success(self, timestamp: float) -> None:
        """Set the ``instana.extension.endpoint.collection.last_success`` gauge.

        Called by the lifecycle manager after each successful collection cycle
        with the current Unix timestamp so consumers can detect stale collectors.
        Emitted on the internal framework health page.

        Args:
            timestamp: Unix timestamp (seconds) of the successful collection.
        """
        self.record_gauge(
            name="instana.extension.endpoint.collection.last_success",
            value=timestamp,
            attributes=self._framework_endpoint_attrs(),
            description="Timestamp of last successful collection",
            unit="s",
            internal=True,
        )
