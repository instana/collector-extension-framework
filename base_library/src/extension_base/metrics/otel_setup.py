# (c) Copyright IBM Corp. 2026
"""
OpenTelemetry SDK initialization for Extension Base Library.

Provides setup_otel(), create_meter_provider(), create_internal_meter_provider(),
and configure_otlp_exporter() for initialising the OTel metrics pipeline from
extension configuration.

Two MeterProviders are created per extension instance:
- **business provider** – resource identity ``service.name=<extension_name>``;
  used for all metrics emitted by the extension developer.
- **internal provider** – resource identity ``service.name=<extension_name>.internal``;
  used exclusively for framework health metrics (collection counts, durations, etc.).

Both providers share the same ``service.instance.id`` / ``container.id`` so the
two Instana service pages can be correlated.
"""

import logging
import os
import socket
from typing import Any

from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter as GRPCMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter as HTTPMetricExporter,
)
from opentelemetry.sdk.metrics import MeterProvider as _MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger(__name__)

_DEFAULT_CA_CERT = "/opt/instana/custom-collector/config/ca.crt"

__all__ = [
    "setup_otel",
    "create_meter_provider",
    "create_internal_meter_provider",
    "configure_otlp_exporter",
]


class MeterProvider(_MeterProvider):
    """MeterProvider subclass that exposes the ``resource`` attribute."""

    def __init__(self, resource: Resource, **kwargs):
        super().__init__(resource=resource, **kwargs)
        self.resource = resource


def _get(config: Any, *keys: str, default: Any = None) -> Any:
    """Safely read nested config fields from either a dict or an object."""
    obj = config
    for key in keys:
        if obj is None:
            return default
        if isinstance(obj, dict):
            obj = obj.get(key, default)
        else:
            obj = getattr(obj, key, default)
    return obj if obj is not None else default


def _apply_proxy_env_vars(config: Any) -> None:
    """Set HTTP_PROXY, HTTPS_PROXY, and NO_PROXY from the otlp config block.

    Called once before the OTLP exporter is constructed so that both the
    gRPC C-core and the HTTP transport pick up the proxy settings.

    If a value is already present in the environment it is left unchanged
    (explicit container env vars take precedence over config file values).

    Args:
        config: Extension configuration (object or dict).
    """
    proxy_fields = (
        ("http_proxy", "HTTP_PROXY"),
        ("https_proxy", "HTTPS_PROXY"),
        ("no_proxy", "NO_PROXY"),
    )
    for config_field, env_var in proxy_fields:
        value = _get(config, "otlp", config_field, default=None)
        if value and not os.environ.get(env_var):
            os.environ[env_var] = value
            logger.debug("Proxy env var set from config: %s", env_var)


def _apply_certificate_env_var(config: Any) -> None:
    """Set OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE from config or the well-known path.

    Precedence (high → low):

    1. ``OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE`` already in the environment —
       left untouched; explicit container env vars always win.
    2. ``otlp.certificate_file`` set in extension-config.json.
    3. ``_DEFAULT_CA_CERT`` exists on disk —
       auto-detected; no config change required from the user.

    Called once before the OTLP exporter is constructed so that both the
    gRPC exporter (ssl_channel_credentials) and the HTTP exporter
    (requests verify=) pick up the CA certificate path.

    Args:
        config: Extension configuration (object or dict).
    """
    if os.environ.get("OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE"):
        return
    cert = _get(config, "otlp", "certificate_file", default=None)
    if not cert and os.path.isfile(_DEFAULT_CA_CERT):
        cert = _DEFAULT_CA_CERT
        logger.debug(
            "CA certificate auto-detected at well-known path: %s", _DEFAULT_CA_CERT
        )
    if cert:
        os.environ["OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE"] = cert
        logger.debug(
            "Certificate env var set: OTEL_EXPORTER_OTLP_METRICS_CERTIFICATE"
        )


def setup_otel(
    config: Any = None,
    *,
    endpoint: str | None = None,
    service_name: str | None = None,
    service_version: str | None = None,
) -> tuple["MeterProvider", "MeterProvider"]:
    """Initialise the OpenTelemetry metrics SDK.

    Returns **two** :class:`MeterProvider` instances — one for business metrics
    and one for internal framework health metrics.  Both point at the same OTLP
    endpoint but carry different ``service.name`` resource attributes so they
    appear on separate pages in the Instana UI.

    Can be called either with a config object/dict, or with explicit
    keyword arguments for testing convenience:

    .. code-block:: python

        # From a full config object or dict
        business_mp, internal_mp = setup_otel(config)

        # With explicit keyword args (test helper form)
        business_mp, internal_mp = setup_otel(
            endpoint="localhost:4317", service_name="my-ext", service_version="1.0"
        )

    Args:
        config: Extension configuration — either an
            :class:`~extension_base.config.models.ExtensionConfig` instance
            or a plain dict with the same structure.
        endpoint: OTLP endpoint override (used when *config* is None).
        service_name: Service name override (used when *config* is None).
        service_version: Service version override (used when *config* is None).

    Returns:
        Tuple of ``(business_meter_provider, internal_meter_provider)``.
    """
    if config is None:
        # Build a minimal synthetic config from explicit kwargs
        config = {
            "extension_name": service_name or "",
            "extension_version": service_version or "",
            "otlp": {"endpoint": endpoint or "localhost:4317"},
        }
    _apply_proxy_env_vars(config)
    _apply_certificate_env_var(config)
    return create_meter_provider(config), create_internal_meter_provider(config)


def _runtime_identity(config: Any) -> tuple[str, str, str]:
    """Resolve the three runtime identity values from env vars with config fallback.

    Priority per attribute:
    - ``service.name``        → SERVICE_NAME        → config.extension_name
    - ``container.id``        → CONTAINER_ID
    - ``service.instance.id`` → SERVICE_INSTANCE_ID → CONTAINER_ID

    Returns:
        Tuple of ``(service_name, service_instance_id, container_id)``.
    """
    service_name = (
        os.environ.get("SERVICE_NAME")
        or _get(config, "extension_name")
        or ""
    )
    container_id = os.environ.get("CONTAINER_ID") or ""
    service_instance_id = (
        os.environ.get("SERVICE_INSTANCE_ID")
        or container_id
    )
    return service_name, service_instance_id, container_id


def _build_resource(config: Any, service_name: str) -> Resource:
    """Build an OTel :class:`Resource` using *service_name* as ``service.name``.

    All other identity attributes are resolved from env vars / config and are
    identical between the business and internal providers so the two Instana
    pages can be correlated via ``service.instance.id``.
    """
    _, service_instance_id, container_id = _runtime_identity(config)

    extension_id = _get(config, "extension_id") or ""
    extension_version = _get(config, "extension_version") or ""
    supervisor_id = _get(config, "supervisor_id") or ""
    deployment_id = _get(config, "deployment_id") or ""

    return Resource.create({
        "service.name": service_name,
        "service.version": extension_version,
        "service.instance.id": service_instance_id,
        "container.id": container_id,
        "host.name": socket.gethostname(),
        "instana.extension.id": extension_id,
        "instana.supervisor.id": supervisor_id,
        "instana.deployment.id": deployment_id,
    })


def _build_meter_provider(config: Any, resource: Resource) -> MeterProvider:
    """Construct a :class:`MeterProvider` wired to the OTLP exporter from *config*."""
    exporter = configure_otlp_exporter(config)
    interval_s = int(_get(config, "otlp", "interval", default=60))
    timeout_s = int(_get(config, "otlp", "timeout", default=10))

    reader = PeriodicExportingMetricReader(
        exporter,
        export_interval_millis=interval_s * 1000,
        export_timeout_millis=timeout_s * 1000,
    )
    return MeterProvider(resource=resource, metric_readers=[reader])


def create_meter_provider(config: Any) -> MeterProvider:
    """Create the **business** :class:`MeterProvider` with resource attributes from *config*.

    ``service.name`` is resolved from the ``SERVICE_NAME`` environment variable
    first, falling back to ``config.extension_name``.

    Args:
        config: Extension configuration (object or dict).

    Returns:
        :class:`MeterProvider` for business (extension developer) metrics.
    """
    service_name, _, _ = _runtime_identity(config)
    resource = _build_resource(config, service_name)
    return _build_meter_provider(config, resource)


def create_internal_meter_provider(config: Any) -> MeterProvider:
    """Create the **internal** :class:`MeterProvider` for framework health metrics.

    Identical to the business provider except ``service.name`` is suffixed with
    ``".internal"``, causing Instana to place these metrics on a separate page
    from the extension's business metrics while keeping the same
    ``service.instance.id`` for cross-page correlation.

    Python runtime metrics (memory, CPU, GC, thread count) are registered
    automatically as observable callbacks on the internal meter.

    Args:
        config: Extension configuration (object or dict).

    Returns:
        :class:`MeterProvider` for internal framework health metrics.
    """
    service_name, _, _ = _runtime_identity(config)
    internal_service_name = f"{service_name}.internal"
    resource = _build_resource(config, internal_service_name)
    provider = _build_meter_provider(config, resource)

    from extension_base.metrics.runtime_metrics import (
        register_python_runtime_metrics,
    )

    meter_name = (
        _get(config, "extension_name") or service_name or __name__
    )
    meter = provider.get_meter(meter_name)
    register_python_runtime_metrics(meter)

    return provider


def _register_threads_active_observable(meter: Any, threads: list) -> None:
    """Register an observable gauge that reports live active thread count.

    The SDK pulls the callback on every export cycle so the value always
    reflects live thread state without a polling loop.

    Args:
        meter: OTel Meter from the internal MeterProvider.
        threads: The live thread list — must be the same object that
                 LifecycleManager mutates in-place, not a copy.
    """
    from typing import Iterable

    from opentelemetry.metrics import CallbackOptions, Observation

    attrs = {"metric.type": "framework"}

    def _observe_active(_options: CallbackOptions) -> Iterable[Observation]:
        yield Observation(
            sum(1 for t in list(threads) if t.is_alive()), attributes=attrs
        )

    meter.create_observable_gauge(
        "instana.extension.threads.active",
        callbacks=[_observe_active],
        description="Number of active collection threads",
        unit="{thread}",
    )


def _resolve_tls(config: Any, instana_key: str | None) -> bool:
    """Resolve whether TLS should be used for the OTLP connection.

    Precedence (high → low):

    1. ``otlp.tls`` explicitly set in config (populated from JSON or the
       ``OTLP_TLS`` env var by :class:`~extension_base.config.loader.ConfigLoader`)
    2. ``instana_key`` present — implies a public SaaS backend — TLS required
    3. Default → ``False`` (plaintext, safe for local/cluster collectors)

    ``otlp.tls`` is expected to be a Python ``bool`` (Pydantic parses JSON
    booleans; the ``OTLP_TLS`` env-var lambda produces one too).  If a raw
    dict is passed with a string value, only the case-insensitive string
    ``"true"`` maps to ``True``; everything else (including ``"false"``,
    ``"0"``) maps to ``False``.

    Args:
        config: Extension configuration (object or dict).
        instana_key: Resolved instana_key value (may be None).

    Returns:
        ``True`` if TLS should be used, ``False`` for plaintext.
    """
    tls_explicit = _get(config, "otlp", "tls", default=None)
    if tls_explicit is not None:
        if isinstance(tls_explicit, str):
            return tls_explicit.strip().lower() == "true"
        return bool(tls_explicit)
    if instana_key:
        return True
    return False


def configure_otlp_exporter(config: Any):
    """Create an OTLP metric exporter from *config*.

    Selects gRPC or HTTP transport based on ``config.otlp.protocol``.
    Supports ``"grpc"`` (default), ``"http/protobuf"``, and ``"http/json"``.

    When ``config.otlp.instana_key`` is set the custom HTTP header
    ``x-instana-key`` is included in every export request, enabling
    direct-to-backend delivery without a local collector.

    TLS is resolved via :func:`_resolve_tls` with the following precedence:

    1. ``otlp.tls`` / ``OTLP_TLS`` env var (explicit override — highest)
    2. ``instana_key`` present (implies public SaaS backend)
    3. Default ``False`` — plaintext for local/cluster collectors

    For HTTP the resolved TLS flag governs the URL scheme when the endpoint
    is a bare hostname: ``https://`` when TLS is enabled, ``http://`` otherwise.
    An endpoint that already contains a scheme is left untouched.

    Args:
        config: Extension configuration (object or dict).

    Returns:
        An OTLP metric exporter instance.
    """
    endpoint = _get(config, "otlp", "endpoint", default="localhost:4317")
    protocol = _get(config, "otlp", "protocol", default="grpc")
    compression_str = _get(config, "otlp", "compression", default="gzip")
    timeout_s = int(_get(config, "otlp", "timeout", default=10))
    instana_key = _get(config, "otlp", "instana_key", default=None)

    # Build the optional header dict (only when a key is provided)
    headers: dict[str, str] = {}
    if instana_key:
        headers["x-instana-key"] = instana_key

    use_tls = _resolve_tls(config, instana_key)

    # Map compression string to OTel enum
    from opentelemetry.exporter.otlp.proto.grpc.exporter import Compression

    if compression_str == "gzip":
        grpc_compression = Compression.Gzip
    else:
        grpc_compression = Compression.NoCompression

    if protocol in ("http/protobuf", "http/json"):
        # Apply scheme to bare hostnames; leave explicit http(s):// untouched.
        if not endpoint.startswith("http"):
            scheme = "https" if use_tls else "http"
            endpoint = f"{scheme}://{endpoint}"
        return HTTPMetricExporter(
            endpoint=f"{endpoint}/v1/metrics",
            timeout=timeout_s,
            headers=headers if headers else None,
        )

    # Default: gRPC
    # Ensure endpoint does NOT have a scheme for gRPC exporter
    if endpoint.startswith("http://"):
        endpoint = endpoint[len("http://"):]
    elif endpoint.startswith("https://"):
        endpoint = endpoint[len("https://"):]

    return GRPCMetricExporter(
        endpoint=endpoint,
        compression=grpc_compression,
        timeout=timeout_s,
        insecure=not use_tls,
        headers=headers if headers else None,
    )
