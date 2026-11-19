# (c) Copyright IBM Corp. 2026
"""
Health reporter for Extension Base Library.

Provides HealthReporter which tracks extension status and exposes a
lightweight HTTP /health endpoint for container health checks.
"""

import json
import logging
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import psutil

__all__ = ["HealthReporter"]

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    """Return current UTC time as an ISO 8601 string."""
    return datetime.now(tz=timezone.utc).isoformat()


class HealthReporter:
    """Tracks extension health status and serves it via an HTTP endpoint.

    Args:
        extension_id: Extension identifier included in every status response.
        container_id: Container identifier included in every status response.
        http_port: TCP port the HTTP server binds to (default: 8080).
        http_bind: Host/IP to bind to (default: ``"localhost"``).
    """

    def __init__(
        self,
        extension_id: str,
        container_id: str,
        http_port: int = 8080,
        http_bind: str = "localhost",
    ) -> None:
        self._extension_id = extension_id
        self._container_id = container_id
        self._http_port = http_port
        self._http_bind = http_bind

        self._lock = threading.Lock()
        self._status: str = "starting"
        self._timestamp: str = _now_iso()
        self._endpoints: dict[str, dict[str, Any]] = {}
        self._metrics: dict[str, Any] = {}

        self._http_server: HTTPServer | None = None
        self._http_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Status reporting
    # ------------------------------------------------------------------

    def report_startup(self) -> None:
        """Set status to ``"starting"`` and record the current timestamp."""
        with self._lock:
            self._status = "starting"
            self._timestamp = _now_iso()

    def update_endpoint_status(
        self,
        endpoint_id: str,
        status: str,
        collections_total: int = 0,
        errors_total: int = 0,
        last_error: str = "",
    ) -> None:
        """Update the status record for a single endpoint.

        Args:
            endpoint_id: Endpoint identifier.
            status: Current status string (e.g. ``"collecting"``, ``"error"``,
                ``"failed"``).
            collections_total: Cumulative collection count increment.
            errors_total: Cumulative error count increment.
            last_error: Optional error message for this endpoint.  Cleared
                automatically when status returns to ``"collecting"``.
        """
        with self._lock:
            existing = self._endpoints.get(endpoint_id, {})
            entry: dict[str, Any] = {
                "status": status,
                "collections_total": existing.get("collections_total", 0)
                + collections_total,
                "errors_total": existing.get("errors_total", 0) + errors_total,
            }
            # Disabled endpoints never run a collection — omit last_collection
            if status != "disabled":
                entry["last_collection"] = _now_iso()
            if last_error:
                entry["last_error"] = last_error
            elif status == "collecting" and "last_error" in existing:
                pass  # cleared by omission — key not carried forward
            elif "last_error" in existing:
                entry["last_error"] = existing["last_error"]  # preserve across non-collecting updates
            self._endpoints[endpoint_id] = entry
            self._timestamp = _now_iso()

    @property
    def _computed_status(self) -> str:
        """Derive top-level status from per-endpoint states.

        Rules (evaluated under ``self._lock`` by callers):
        - No endpoints registered yet → fall back to ``self._status`` (``"starting"``).
        - Any endpoint in ``"failed"`` → ``"unhealthy"`` (thread dead, no recovery possible).
        - Any endpoint in ``"error"`` (thread alive, back-off retrying) → ``"degraded"``.
        - All endpoints ``"disabled"`` → ``"idle"`` (process is live but collecting nothing).
        - Otherwise → ``"healthy"``.

        ``"error"`` and ``"failed"`` are intentionally treated differently:
        - ``"error"``: collection thread is still alive and retrying with back-off.
        - ``"failed"``: back-off exhausted, thread has exited. Only a restart can
          recover this endpoint. HTTP 503 is reserved exclusively for this state.

        ``"idle"`` maps to HTTP 200 — the process is healthy from the orchestrator's
        perspective; an operator disabled all endpoints intentionally.
        """
        if not self._endpoints:
            return self._status
        statuses = [ep["status"] for ep in self._endpoints.values()]
        if any(s == "failed" for s in statuses):
            return "unhealthy"
        if any(s == "error" for s in statuses):
            return "degraded"
        if all(s == "disabled" for s in statuses):
            return "idle"
        return "healthy"

    def get_status(self) -> dict[str, Any]:
        """Return the current health status as a plain dict.

        The top-level ``"status"`` field is derived from per-endpoint states
        via ``_computed_status``.  ``"endpoints_failing"`` is the count of
        endpoints currently in ``"error"`` or ``"failed"`` state.

        Returns:
            Dict with keys: ``status``, ``timestamp``, ``extension_id``,
            ``container_id``, ``endpoints``, ``resources``, ``metrics``.
        """
        with self._lock:
            proc = psutil.Process()
            mem = proc.memory_percent()
            threads = proc.num_threads()

            computed = self._computed_status
            endpoints_healthy = endpoints_disabled = endpoints_failing = 0
            for ep in self._endpoints.values():
                s = ep.get("status")
                if s == "collecting":
                    endpoints_healthy += 1
                elif s == "disabled":
                    endpoints_disabled += 1
                elif s in ("error", "failed"):
                    endpoints_failing += 1

            return {
                "status": computed,
                "timestamp": self._timestamp,
                "extension_id": self._extension_id,
                "container_id": self._container_id,
                "endpoints": dict(self._endpoints),
                "resources": {
                    "memory_usage_percent": round(mem, 2),
                    "thread_count": threads,
                },
                "metrics": {
                    **self._metrics,
                    "endpoints_healthy": endpoints_healthy,
                    "endpoints_disabled": endpoints_disabled,
                    "endpoints_failing": endpoints_failing,
                },
            }

    # ------------------------------------------------------------------
    # HTTP server
    # ------------------------------------------------------------------

    def start_http_server(self) -> None:
        """Start the HTTP health endpoint server in a background daemon thread.

        Binds to ``http_bind:http_port`` and serves GET /health.
        Safe to call multiple times (stops existing server first).
        """
        if self._http_server is not None:
            self.stop_http_server()

        reporter = self  # capture for closure

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                if self.path == "/health":
                    status = reporter.get_status()
                    body = json.dumps(status).encode()
                    http_code = (
                        503
                        if status["status"] == "unhealthy"
                        else 200  # healthy / degraded / starting → 200
                    )
                    self.send_response(http_code)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):  # silence access log
                pass

        server = HTTPServer((self._http_bind, self._http_port), _Handler)
        self._http_server = server

        thread = threading.Thread(
            target=server.serve_forever,
            daemon=True,
            name=f"health-http-{self._http_port}",
        )
        self._http_thread = thread
        thread.start()
        logger.debug(
            "Health HTTP server started on %s:%d",
            self._http_bind,
            self._http_port,
        )

    def stop_http_server(self) -> None:
        """Stop the HTTP health endpoint server and join its thread.

        The ``_http_thread`` reference is retained after stopping so callers
        can still check ``_http_thread.is_alive() == False``.
        """
        if self._http_server is not None:
            self._http_server.shutdown()
            self._http_server.server_close()
            self._http_server = None
        if self._http_thread is not None:
            self._http_thread.join(timeout=5)
            # Keep reference — callers may still check is_alive() after stop
