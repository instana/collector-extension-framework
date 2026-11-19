# (c) Copyright IBM Corp. 2026
"""
Lifecycle manager for Extension Base Library.

Manages extension startup, shutdown, signal handling, and per-endpoint
collection threads.
"""

import contextlib
import logging
import signal
import threading
import time
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from extension_base import ExtensionConfig, HealthReporter
    from opentelemetry.sdk.metrics import MeterProvider

__all__ = ["LifecycleManager"]

logger = logging.getLogger(__name__)

_DEFAULT_MAX_THREADS = 35
_DEFAULT_SHUTDOWN_TIMEOUT = 30
_MAX_BACKOFF_SECONDS = 60


class LifecycleManager:
    """Manages the extension lifecycle: startup, collection threads, shutdown.

    Args:
        config: Extension configuration (dict or ExtensionConfig).
        health_reporter: HealthReporter instance to notify of state changes.
        meter_provider: Optional OTel MeterProvider — shutdown() will call
            its ``.shutdown()`` method.
        retry_on_failure: Retry collection on failure with exponential back-off.
            The thread exits when the back-off reaches ``_MAX_BACKOFF_SECONDS``
            (62 s worst-case total wait across 5 sleeps before exit on attempt 6).
        max_threads: Maximum number of concurrent collection threads.
    """

    def __init__(
        self,
        config: "ExtensionConfig",
        health_reporter: "HealthReporter",
        meter_provider: "MeterProvider | None" = None,
        internal_meter_provider: "MeterProvider | None" = None,
        retry_on_failure: bool = True,
        max_threads: int = _DEFAULT_MAX_THREADS,
    ) -> None:
        self._config = config
        self._health_reporter = health_reporter
        self._meter_provider = meter_provider
        self._internal_meter_provider = internal_meter_provider
        self._retry_on_failure = retry_on_failure
        self._max_threads = max_threads

        self._shutdown_flag = threading.Event()
        self._threads: list[threading.Thread] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, collection_func: Callable) -> None:
        """Start one collection thread per configured endpoint.

        Returns immediately; threads run as daemons in the background.

        Args:
            collection_func: Callable with signature
                ``(endpoint: dict, emitter: Any) -> None`` called
                repeatedly until shutdown is requested.
        """
        self._shutdown_flag.clear()
        self._threads.clear()  # must clear in-place — reassigning would break the closure

        endpoints = self._get_endpoints()
        enabled_endpoints, disabled_endpoints = [], []
        for ep in endpoints:
            if _endpoint_enabled(ep):
                enabled_endpoints.append(ep)
            else:
                disabled_endpoints.append(ep)

        # Report disabled endpoints in the health summary so operators can
        # distinguish "intentionally skipped" from "not started yet".
        for ep in disabled_endpoints:
            ep_id = _endpoint_id(ep)
            logger.info("Endpoint %s is disabled - skipping collection", ep_id)
            self._health_reporter.update_endpoint_status(
                endpoint_id=ep_id,
                status="disabled",
                collections_total=0,
                errors_total=0,
            )

        for endpoint in enabled_endpoints[: self._max_threads]:
            thread = threading.Thread(
                target=self._run_endpoint,
                args=(endpoint, collection_func),
                daemon=True,
                name=f"collection-{_endpoint_id(endpoint)}",
            )
            self._threads.append(thread)
            thread.start()

        # Register an observable gauge for threads.active on the internal provider.
        # The SDK calls the callback on every export cycle, so the value always
        # reflects the live thread state without a polling loop.
        self._register_threads_active_observable()


    def shutdown(
        self, timeout_seconds: float = _DEFAULT_SHUTDOWN_TIMEOUT
    ) -> None:
        """Signal all collection threads to stop and wait for them to finish.

        Args:
            timeout_seconds: Maximum seconds to wait per thread before
                abandoning the join (thread is left as a daemon).
        """
        self._shutdown_flag.set()

        deadline = time.time() + timeout_seconds
        for thread in self._threads:
            remaining = max(0.0, deadline - time.time())
            thread.join(timeout=remaining)

        # Flush metrics — shut down both providers
        for mp in (self._meter_provider, self._internal_meter_provider):
            if mp is not None:
                try:
                    mp.shutdown()
                except Exception:
                    logger.exception("Error shutting down meter provider")

    def register_shutdown_handler(self) -> None:
        """Register SIGTERM and SIGINT handlers that call :meth:`shutdown`.

        Must be called from the main thread. When called from a non-main
        thread ``signal.signal`` raises ``ValueError``; this method catches
        that and logs a warning instead of propagating the error.
        """
        try:
            signal.signal(signal.SIGTERM, self._handle_signal)
            signal.signal(signal.SIGINT, self._handle_signal)
        except ValueError:
            logger.warning(
                "register_shutdown_handler() called from non-main thread — "
                "signal handlers not registered"
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _register_threads_active_observable(self) -> None:
        """Resolve the internal meter and register the threads.active observable gauge.

        Delegates instrument creation to
        :func:`~extension_base.metrics.otel_setup._register_threads_active_observable`
        so all OTel SDK usage stays in ``otel_setup``.
        """
        from extension_base.metrics.otel_setup import _register_threads_active_observable

        mp = self._internal_meter_provider or self._meter_provider
        if mp is None:
            return

        if isinstance(self._config, dict):
            meter_name = self._config.get("extension_name") or __name__
        else:
            meter_name = getattr(self._config, "extension_name", None) or __name__

        _register_threads_active_observable(mp.get_meter(meter_name), self._threads)

    def _handle_signal(self, signum: int, frame: Any) -> None:
        """Signal handler — triggers graceful shutdown."""
        logger.info("Received signal %d - initiating shutdown", signum)
        self._shutdown_flag.set()

    def _get_endpoints(self) -> list[Any]:
        """Return the list of endpoint configs from the extension config.

        When config is a plain dict, converts each endpoint dict to a
        SimpleNamespace so collection functions can use attribute access
        (``endpoint.id``, ``endpoint.tags``, etc.).
        """
        if isinstance(self._config, dict):
            raw = self._config.get("configuration", {}).get("endpoints", [])
            return [
                ep if not isinstance(ep, dict) else SimpleNamespace(**ep)
                for ep in raw
            ]
        return (
            getattr(
                getattr(self._config, "configuration", None), "endpoints", []
            )
            or []
        )

    def _run_endpoint(self, endpoint: Any, collection_func: Callable) -> None:
        """Target for each collection thread.

        Runs *collection_func* in a tight loop (with sleep based on endpoint
        interval) until the shutdown flag is set.  On exception, reports to
        the health reporter and optionally restarts.
        """
        # Belt-and-suspenders: if somehow called directly for a disabled endpoint, bail out.
        if not _endpoint_enabled(endpoint):
            return

        from extension_base.metrics.emitter import MetricsEmitter
        from extension_base.metrics.otel_setup import setup_otel

        endpoint_id = _endpoint_id(endpoint)
        retry_count = 0

        # Use the extension_name as the meter (instrumentation scope) name so
        # that Instana displays metrics as "<extension_name>/*" instead
        # of the internal module path "extension_base.lifecycle.manager/…".
        if isinstance(self._config, dict):
            meter_name = self._config.get("extension_name") or __name__
        else:
            meter_name = getattr(self._config, "extension_name", None) or __name__

        # Build emitter once per thread — obtain meters from both providers
        if self._meter_provider is not None:
            meter = self._meter_provider.get_meter(meter_name)
            internal_mp = self._internal_meter_provider or self._meter_provider
            internal_meter = internal_mp.get_meter(meter_name)
        else:
            _business_mp, _internal_mp = setup_otel(self._config)
            meter = _business_mp.get_meter(meter_name)
            internal_meter = _internal_mp.get_meter(meter_name)
        emitter = MetricsEmitter(meter=meter, endpoint=endpoint, internal_meter=internal_meter)

        while not self._shutdown_flag.is_set():
            try:
                t0 = time.monotonic()
                emitter.record_collection_total()

                collection_func(endpoint, emitter)

                emitter.record_collection_duration((time.monotonic() - t0) * 1000)
                emitter.record_collection_success()
                emitter.record_collection_last_success(time.time())
                retry_count = 0  # consecutive failure chain broken
                self._health_reporter.update_endpoint_status(
                    endpoint_id=endpoint_id,
                    status="collecting",
                    collections_total=1,
                    errors_total=0,
                )
            except Exception as exc:
                emitter.record_collection_failure()
                logger.exception(
                    "Collection error for endpoint %s: %s", endpoint_id, exc
                )
                with contextlib.suppress(Exception):
                    self._health_reporter.update_endpoint_status(
                        endpoint_id=endpoint_id,
                        status="error",
                        collections_total=0,
                        errors_total=1,
                        last_error=str(exc),
                    )

                if self._retry_on_failure:
                    retry_count += 1
                    back_off = min(2 ** retry_count, _MAX_BACKOFF_SECONDS)
                    if back_off >= _MAX_BACKOFF_SECONDS:
                        cumulative = sum(
                            min(2**i, _MAX_BACKOFF_SECONDS)
                            for i in range(1, retry_count)
                        )
                        logger.error(
                            "Endpoint %s unreachable after %d attempts (~%d s total back-off), stopping thread",
                            endpoint_id,
                            retry_count,
                            cumulative,
                        )
                        self._health_reporter.update_endpoint_status(
                            endpoint_id=endpoint_id,
                            status="failed",
                            last_error=f"Endpoint {endpoint_id} unreachable after maximum back-off",
                        )
                        break
                    logger.warning(
                        "Collection failed for endpoint %s (attempt %d), retrying in %d s",
                        endpoint_id,
                        retry_count,
                        back_off,
                    )
                    self._shutdown_flag.wait(timeout=back_off)
                    continue
                # Not configured to retry — exit loop immediately
                self._health_reporter.update_endpoint_status(
                    endpoint_id=endpoint_id,
                    status="failed",
                    last_error=f"Collection failed for endpoint {endpoint_id}: {exc}",
                )
                break

            # Respect shutdown between collections
            interval = _endpoint_interval(endpoint)
            self._shutdown_flag.wait(timeout=interval)

        # Thread is exiting — increment the completed counter once.
        emitter.record_threads_completed()

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _endpoint_id(endpoint: Any) -> str:
    """Extract endpoint id from dict or object."""
    if isinstance(endpoint, dict):
        return str(endpoint.get("id", "unknown"))
    return str(getattr(endpoint, "id", "unknown"))


def _endpoint_interval(endpoint: Any) -> float:
    """Extract collection interval (seconds) from endpoint config."""
    if isinstance(endpoint, dict):
        return float(endpoint.get("interval", 60))
    return float(getattr(endpoint, "interval", 60) or 60)


def _endpoint_enabled(endpoint: Any) -> bool:
    """Return True unless the endpoint config explicitly sets ``enabled=False``.

    Works with dict configs, ``Endpoint`` objects, and ``SimpleNamespace``
    so the lifecycle manager accepts all three forms.
    """
    if isinstance(endpoint, dict):
        return bool(endpoint.get("enabled", True))
    return bool(getattr(endpoint, "enabled", True))
