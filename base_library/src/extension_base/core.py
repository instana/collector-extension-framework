# (c) Copyright IBM Corp. 2026
"""
Core ExtensionBase class — main entry point for building extensions.

Orchestrates configuration loading, OTel setup, health reporting, and
lifecycle management into a single high-level interface.
"""

import logging
import os
from typing import Any, Callable

__all__ = ["ExtensionBase"]

logger = logging.getLogger(__name__)


class ExtensionBase:
    """High-level orchestrator for extension lifecycle.

    Initialises all sub-components during construction so that the
    initialization order is deterministic and patchable in tests:
    1. ConfigLoader  (config + credentials)
    2. setup_otel    (OTel MeterProvider)
    3. HealthReporter
    4. LifecycleManager

    ``run(collection_func)`` then starts the server, threads, and blocks.

    Args:
        http_port: Port for the HTTP health endpoint.  Defaults to the value
            of the ``INSTANA_HEALTH_PORT`` environment variable, falling back
            to ``8080``.  The Supervisor injects ``INSTANA_HEALTH_PORT`` at
            container creation time so that multiple extension containers on
            the same host can each use a distinct port without conflict.
        http_bind: Host/IP to bind the health endpoint to.
    """

    def __init__(
        self,
        http_port: int = int(os.environ.get("INSTANA_HEALTH_PORT", 8080)),
        http_bind: str = "0.0.0.0",
    ) -> None:
        # Late imports so that test patches on source modules take effect
        from extension_base.config.loader import ConfigLoader
        from extension_base.health.reporter import HealthReporter
        from extension_base.lifecycle.manager import LifecycleManager
        from extension_base.metrics.otel_setup import setup_otel
        from extension_base.logging import setup_logging

        self._http_port = http_port
        self._http_bind = http_bind

        # 1. Load configuration
        loader = ConfigLoader()
        self._config = loader.load()

        # 1a. Apply the configured log level after config resolution.
        #     setup_logging() also honors INSTANA_LOG_LEVEL, which overrides
        #     the config value when present.
        log_level = getattr(
            getattr(self._config, "configuration", None), "log_level", None
        )
        setup_logging(level=log_level)

        # 2. Initialise OTel — returns (business_provider, internal_provider)
        self._meter_provider, self._internal_meter_provider = setup_otel(self._config)

        # 3. Health reporter (not started until run())
        self._health_reporter = HealthReporter(
            extension_id=self._config.extension_id,
            container_id=self._config.container_id or "",
            http_port=http_port,
            http_bind=http_bind,
        )

        # 4. Lifecycle manager
        self._lifecycle = LifecycleManager(
            config=self._config,
            health_reporter=self._health_reporter,
            meter_provider=self._meter_provider,
            internal_meter_provider=self._internal_meter_provider,
        )

        # Register signal handlers now, while we are still on the main thread.
        # run() may be called from a background thread (e.g. in tests), where
        # signal.signal() would raise ValueError.
        self._lifecycle.register_shutdown_handler()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_config(self) -> Any:
        """Return the loaded ExtensionConfig.

        Returns:
            The fully resolved extension configuration.
        """
        return self._config

    def run(self, collection_func: Callable) -> None:
        """Start the extension and block until :meth:`shutdown` is called.

        Starts the health HTTP server, registers signal handlers, launches
        one collection thread per endpoint, then blocks on the shutdown flag.

        Args:
            collection_func: ``(endpoint, emitter) -> None`` called per-endpoint.
        """
        self._health_reporter.start_http_server()
        self._health_reporter.report_startup()

        self._lifecycle.start(collection_func)

        # Block until shutdown is signalled
        self._lifecycle._shutdown_flag.wait()

        # Cleanup
        self._health_reporter.stop_http_server()

    def shutdown(self, timeout_seconds: float = 30) -> None:
        """Trigger graceful shutdown.

        Safe to call from any thread, including signal handlers.

        Args:
            timeout_seconds: Maximum time to wait for collection threads.
        """
        if self._lifecycle is not None:
            self._lifecycle.shutdown(timeout_seconds=timeout_seconds)
