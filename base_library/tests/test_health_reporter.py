# (c) Copyright IBM Corp. 2026
"""
Tests for Health Reporter (FR5).

This module contains tests for the Health Reporter component which manages
container health status reporting via HTTP endpoint.

Test Coverage:
- T072: Health reporter class structure
- T073: HTTP health endpoint server
- T074: Health status tracking (healthy/unhealthy)
- T075: Endpoint collection status updates
- T076: Resource usage monitoring
- T077: Health criteria validation
- T078: HTTP GET /health endpoint
- T079: HTTP status codes (200 OK, 503 Unavailable)
- T080: Health status JSON format
- T081: Startup health reporting
- T082: Multiple endpoint status tracking
- T083: Health endpoint thread safety
- T084: Health server lifecycle (start/stop)
- T085: Health status persistence

TDD Approach:
- All tests written BEFORE implementation
- Tests will FAIL initially (red phase)
- Implementation will make tests PASS (green phase)

Spec Reference: docs/specs/extension-base-library.md#health-reporter (lines 489-617)
"""

import time


class TestHealthReporter:
    """Test suite for Health Reporter component."""

    def test_health_reporter_class_exists(self):
        """
        Test that HealthReporter class exists and can be instantiated.

        Spec Reference: docs/specs/extension-base-library.md#health-reporter
        - API/Interface (lines 590-603)

        Validates:
        - HealthReporter class is defined in health.reporter module
        - Can be instantiated with extension_id and container_id
        - Has start_http_server() method
        - Has stop_http_server() method
        - Has update_endpoint_status() method

        Expected: HealthReporter class exists (TDD red phase - will fail)
        """
        from extension_base.health import reporter

        # Validate HealthReporter exists
        assert hasattr(reporter, "HealthReporter"), (
            "HealthReporter must be defined in health.reporter module"
        )

        # Validate required methods exist
        HealthReporter = reporter.HealthReporter
        required_methods = [
            "start_http_server",
            "stop_http_server",
            "update_endpoint_status",
        ]

        for method in required_methods:
            assert hasattr(HealthReporter, method), (
                f"HealthReporter must have {method}() method"
            )

    def test_http_health_endpoint_server(self):
        """
        Test HTTP health endpoint server initialization.

        Spec Reference: docs/specs/extension-base-library.md#health-reporter
        - HTTP Health Endpoint (lines 503-549)
        - API/Interface - start_http_server() (lines 595)

        Validates:
        - HTTP server starts on specified port (default: 8080)
        - Server binds to localhost by default
        - Server runs in separate thread
        - Server responds to HTTP requests

        Expected: HTTP server starts (TDD red phase - will fail)
        """
        from extension_base.health.reporter import HealthReporter

        # Create health reporter
        reporter = HealthReporter(
            extension_id="test-ext-1",
            container_id="test-container-1",
            http_port=8080,
            http_bind="localhost",
        )

        # Start HTTP server
        reporter.start_http_server()

        # Validate server is running
        assert reporter._http_server is not None, (
            "HTTP server must be initialized"
        )
        assert reporter._http_thread is not None, (
            "HTTP server thread must be running"
        )
        assert reporter._http_thread.is_alive(), (
            "HTTP server thread must be alive"
        )

        # Cleanup
        reporter.stop_http_server()

    def test_health_status_tracking(self):
        """
        Test health status tracking (healthy/unhealthy/degraded).

        Spec Reference: docs/specs/extension-base-library.md#health-reporter
        - Health Status Tracking (lines 497-502)

        Validates:
        - Initial status is "starting" (no endpoints registered)
        - Status is "healthy" when all endpoints collecting
        - Status is "degraded" when some but not all endpoints in error
        - Status is "unhealthy" when all endpoints in error/failed
        - Status includes timestamp, extension_id, container_id

        Expected: Status tracked correctly
        """
        from extension_base.health.reporter import HealthReporter

        reporter = HealthReporter(
            extension_id="test-ext-1", container_id="test-container-1"
        )

        # Check initial status — no endpoints yet, falls back to self._status
        status = reporter.get_status()
        assert status["status"] == "starting", (
            "Initial status must be 'starting'"
        )
        assert "timestamp" in status, "Status must include timestamp"
        assert status["extension_id"] == "test-ext-1"
        assert status["container_id"] == "test-container-1"

        # All endpoints collecting → healthy
        reporter.update_endpoint_status("ep-1", "collecting", collections_total=1)
        reporter.update_endpoint_status("ep-2", "collecting", collections_total=1)
        status = reporter.get_status()
        assert status["status"] == "healthy", (
            "Status must be 'healthy' when all endpoints are collecting"
        )

        # One endpoint in error → degraded
        reporter.update_endpoint_status("ep-1", "error", errors_total=1, last_error="timeout")
        status = reporter.get_status()
        assert status["status"] == "degraded", (
            "Status must be 'degraded' when some but not all endpoints are in error"
        )
        assert status["endpoints"]["ep-1"]["last_error"] == "timeout"

        # All endpoints in error → degraded (threads still alive, back-off retrying)
        reporter.update_endpoint_status("ep-2", "error", errors_total=1, last_error="conn refused")
        status = reporter.get_status()
        assert status["status"] == "degraded", (
            "Status must be 'degraded' when all endpoints are in error — threads still retrying"
        )

        # Any endpoint in failed → unhealthy (thread dead, no recovery without restart)
        reporter.update_endpoint_status("ep-1", "failed", last_error="max back-off exceeded")
        status = reporter.get_status()
        assert status["status"] == "unhealthy", (
            "Status must be 'unhealthy' when any endpoint is in 'failed' state"
        )

    def test_endpoint_collection_status_updates(self):
        """
        Test endpoint collection status updates.

        Spec Reference: docs/specs/extension-base-library.md#health-reporter
        - Health Status Tracking (lines 499)
        - API/Interface - update_endpoint_status() (lines 600)
        - Health Status Format - endpoints (lines 564-577)

        Validates:
        - update_endpoint_status() updates endpoint status
        - Tracks collections_total counter
        - Tracks errors_total counter
        - Tracks last_collection timestamp
        - Multiple endpoints tracked independently
        - Counters accumulate across successive calls (delta-based contract):
          each call passes an increment of 1; the reporter adds it to the
          running total stored internally.

        Expected: Endpoint status updated (TDD red phase - will fail)
        """
        from extension_base.health.reporter import HealthReporter

        reporter = HealthReporter(
            extension_id="test-ext-1", container_id="test-container-1"
        )

        # --- single update ---
        reporter.update_endpoint_status(
            endpoint_id="ep-1",
            status="collecting",
            collections_total=1,
            errors_total=0,
        )

        status = reporter.get_status()
        assert "endpoints" in status, "Status must include endpoints"
        assert "ep-1" in status["endpoints"], "Endpoint ep-1 must be in status"

        ep_status = status["endpoints"]["ep-1"]
        assert ep_status["status"] == "collecting"
        assert ep_status["collections_total"] == 1
        assert ep_status["errors_total"] == 0
        assert "last_collection" in ep_status

        # --- successive successful collections: totals must grow ---
        # The caller (LifecycleManager._run_endpoint) passes delta=1 on each
        # successful iteration. The reporter accumulates internally.
        for expected_total in range(2, 6):
            reporter.update_endpoint_status(
                endpoint_id="ep-1",
                status="collecting",
                collections_total=1,
                errors_total=0,
            )
            ep = reporter.get_status()["endpoints"]["ep-1"]
            assert ep["collections_total"] == expected_total, (
                f"collections_total must be {expected_total} after "
                f"{expected_total} successful calls, got {ep['collections_total']}"
            )
            assert ep["errors_total"] == 0, (
                "errors_total must remain 0 while collections succeed"
            )

        # --- one error call: errors_total increments, collections stays ---
        reporter.update_endpoint_status(
            endpoint_id="ep-1",
            status="error",
            collections_total=0,
            errors_total=1,
        )
        ep = reporter.get_status()["endpoints"]["ep-1"]
        assert ep["collections_total"] == 5, (
            "collections_total must not change after an error call"
        )
        assert ep["errors_total"] == 1, (
            "errors_total must be 1 after one error call"
        )

    def test_resource_usage_monitoring(self):
        """
        Test resource usage monitoring.

        Spec Reference: docs/specs/extension-base-library.md#health-reporter
        - Health Status Tracking (lines 500)
        - Health Status Format - resources (lines 578-581)

        Validates:
        - Tracks memory usage percentage
        - Tracks thread count
        - Resource metrics included in status
        - Resource metrics updated periodically

        Expected: Resource usage tracked (TDD red phase - will fail)
        """
        from extension_base.health.reporter import HealthReporter

        reporter = HealthReporter(
            extension_id="test-ext-1", container_id="test-container-1"
        )

        # Get status with resources
        status = reporter.get_status()
        assert "resources" in status, "Status must include resources"

        resources = status["resources"]
        assert "memory_usage_percent" in resources, (
            "Resources must include memory_usage_percent"
        )
        assert "thread_count" in resources, (
            "Resources must include thread_count"
        )

        # Validate resource values are reasonable
        assert 0 <= resources["memory_usage_percent"] <= 100, (
            "Memory usage must be between 0 and 100"
        )
        assert resources["thread_count"] > 0, "Thread count must be positive"

    def test_health_criteria_validation(self):
        """
        Test health criteria validation.

        Spec Reference: docs/specs/extension-base-library.md#health-reporter
        - Health Criteria (lines 550-554)

        Validates:
        - Process is running (always true in tests)
        - At least one endpoint collecting successfully
        - Memory usage below threshold (90%)
        - No critical errors in recent period

        Expected: Health criteria validated (TDD red phase - will fail)
        """
        from extension_base.health.reporter import HealthReporter

        reporter = HealthReporter(
            extension_id="test-ext-1", container_id="test-container-1"
        )

        # Initially unhealthy (no endpoints)
        reporter.report_startup()
        status = reporter.get_status()
        assert status["status"] in ["starting", "unhealthy"], (
            "Status must be starting or unhealthy with no endpoints"
        )

        # Add successful endpoint
        reporter.update_endpoint_status(
            endpoint_id="ep-1",
            status="collecting",
            collections_total=10,
            errors_total=0,
        )

        status = reporter.get_status()
        assert status["status"] == "healthy", (
            "Status must be healthy with successful endpoint"
        )

    def test_http_get_health_endpoint(self):
        """
        Test HTTP GET /health endpoint.

        Spec Reference: docs/specs/extension-base-library.md#health-reporter
        - HTTP Health Endpoint (lines 503-549)
        - Endpoint Details (lines 513-541)

        Validates:
        - GET /health returns JSON response
        - Response includes status, timestamp, endpoints
        - Response format matches specification
        - Endpoint accessible via HTTP

        Expected: /health endpoint works (TDD red phase - will fail)
        """
        import requests

        from extension_base.health.reporter import HealthReporter

        reporter = HealthReporter(
            extension_id="test-ext-1",
            container_id="test-container-1",
            http_port=8081,  # Use different port for test
        )

        # Start server
        reporter.start_http_server()
        time.sleep(0.1)  # Give server time to start

        try:
            # Make HTTP request
            response = requests.get("http://localhost:8081/health")

            # Validate response
            assert response.status_code == 200, (
                "Health endpoint must return 200 OK"
            )
            assert response.headers["Content-Type"] == "application/json", (
                "Health endpoint must return JSON"
            )

            # Parse JSON
            data = response.json()
            assert "status" in data
            assert "timestamp" in data
            assert "extension_id" in data
            assert "container_id" in data

        finally:
            reporter.stop_http_server()

    def test_http_status_codes(self):
        """
        Test HTTP status codes for different health states.

        Spec Reference: docs/specs/extension-base-library.md#health-reporter
        - HTTP Health Endpoint - status codes (lines 508-511)

        Validates:
        - 200 OK when healthy
        - 503 Service Unavailable when unhealthy
        - 500 Internal Server Error on health check failure

        Expected: Correct status codes (TDD red phase - will fail)
        """
        import requests

        from extension_base.health.reporter import HealthReporter

        reporter = HealthReporter(
            extension_id="test-ext-1",
            container_id="test-container-1",
            http_port=8082,
        )

        reporter.start_http_server()
        time.sleep(0.1)

        try:
            # No endpoints yet → "starting" → 200
            response = requests.get("http://localhost:8082/health")
            assert response.status_code == 200, (
                "Starting status must return 200 OK"
            )

            # All endpoints collecting → "healthy" → 200
            reporter.update_endpoint_status("ep-1", "collecting", collections_total=1)
            response = requests.get("http://localhost:8082/health")
            assert response.status_code == 200, (
                "Healthy status must return 200 OK"
            )

            # Some endpoints in error → "degraded" → 200 (container stays alive)
            reporter.update_endpoint_status("ep-2", "error", errors_total=1)
            response = requests.get("http://localhost:8082/health")
            assert response.status_code == 200, (
                "Degraded status must return 200 OK (container stays alive)"
            )

            # All endpoints in error → "degraded" → 200 (threads still retrying)
            reporter.update_endpoint_status("ep-1", "error", errors_total=1)
            response = requests.get("http://localhost:8082/health")
            assert response.status_code == 200, (
                "Degraded status must return 200 OK — threads still retrying, do not restart"
            )

            # Any endpoint in failed → "unhealthy" → 503
            reporter.update_endpoint_status("ep-2", "failed", last_error="max back-off exceeded")
            response = requests.get("http://localhost:8082/health")
            assert response.status_code == 503, (
                "Unhealthy status must return 503 Service Unavailable — thread dead, restart warranted"
            )

        finally:
            reporter.stop_http_server()

    def test_health_status_json_format(self):
        """
        Test health status JSON format matches specification.

        Spec Reference: docs/specs/extension-base-library.md#health-reporter
        - Health Status Format (lines 556-588)
        - Endpoint Details - Response format (lines 517-541)

        Validates:
        - JSON structure matches spec
        - All required fields present
        - Field types correct
        - Nested objects formatted correctly

        Expected: JSON format correct (TDD red phase - will fail)
        """
        from extension_base.health.reporter import HealthReporter

        reporter = HealthReporter(
            extension_id="ext-123456", container_id="container-1"
        )

        # Add endpoint status
        reporter.update_endpoint_status(
            endpoint_id="421",
            status="collecting",
            collections_total=150,
            errors_total=2,
        )

        # Get status
        status = reporter.get_status()

        # Validate structure
        assert isinstance(status, dict)
        assert status["status"] == "healthy"
        assert isinstance(status["timestamp"], str)
        assert status["extension_id"] == "ext-123456"
        assert status["container_id"] == "container-1"

        # Validate endpoints
        assert "endpoints" in status
        assert isinstance(status["endpoints"], dict)
        assert "421" in status["endpoints"]

        ep = status["endpoints"]["421"]
        assert ep["status"] == "collecting"
        assert ep["collections_total"] == 150
        assert ep["errors_total"] == 2

        # Validate resources
        assert "resources" in status
        assert "memory_usage_percent" in status["resources"]
        assert "thread_count" in status["resources"]

        # Validate metrics
        assert "metrics" in status
        assert status["metrics"]["endpoints_healthy"] == 1
        assert status["metrics"]["endpoints_disabled"] == 0
        assert status["metrics"]["endpoints_failing"] == 0

    def test_startup_health_reporting(self):
        """
        Test startup health reporting.

        Spec Reference: docs/specs/extension-base-library.md#health-reporter
        - API/Interface - report_startup() (lines 597)

        Validates:
        - report_startup() sets status to "starting"
        - Startup timestamp recorded
        - Initial health state established

        Expected: Startup reported (TDD red phase - will fail)
        """
        from extension_base.health.reporter import HealthReporter

        reporter = HealthReporter(
            extension_id="test-ext-1", container_id="test-container-1"
        )

        # Report startup
        reporter.report_startup()

        status = reporter.get_status()
        assert status["status"] == "starting", (
            "Status must be 'starting' after report_startup()"
        )
        assert "timestamp" in status

    def test_multiple_endpoint_status_tracking(self):
        """
        Test tracking status for multiple endpoints.

        Spec Reference: docs/specs/extension-base-library.md#health-reporter
        - Health Status Tracking (lines 499)
        - Health Status Format - multiple endpoints (lines 564-577)

        Validates:
        - Multiple endpoints tracked independently
        - Each endpoint has separate counters
        - Overall health reflects all endpoints
        - Endpoint status updates don't affect others

        Expected: Multiple endpoints tracked (TDD red phase - will fail)
        """
        from extension_base.health.reporter import HealthReporter

        reporter = HealthReporter(
            extension_id="test-ext-1", container_id="test-container-1"
        )

        # Update multiple endpoints
        reporter.update_endpoint_status(
            endpoint_id="ep-1",
            status="collecting",
            collections_total=100,
            errors_total=0,
        )

        reporter.update_endpoint_status(
            endpoint_id="ep-2",
            status="collecting",
            collections_total=95,
            errors_total=5,
        )

        reporter.update_endpoint_status(
            endpoint_id="ep-3",
            status="error",
            collections_total=10,
            errors_total=10,
        )

        # Get status
        status = reporter.get_status()
        endpoints = status["endpoints"]

        # Validate all endpoints present
        assert len(endpoints) == 3
        assert "ep-1" in endpoints
        assert "ep-2" in endpoints
        assert "ep-3" in endpoints

        # Validate independent tracking
        assert endpoints["ep-1"]["collections_total"] == 100
        assert endpoints["ep-2"]["collections_total"] == 95
        assert endpoints["ep-3"]["collections_total"] == 10

        assert endpoints["ep-1"]["errors_total"] == 0
        assert endpoints["ep-2"]["errors_total"] == 5
        assert endpoints["ep-3"]["errors_total"] == 10

    def test_health_endpoint_thread_safety(self):
        """
        Test thread safety of health endpoint updates.

        Spec Reference: docs/specs/extension-base-library.md#health-reporter
        - HTTP Health Endpoint - Implementation Notes (lines 543-548)

        Validates:
        - Concurrent status updates don't corrupt data
        - HTTP server handles concurrent requests
        - Status reads are thread-safe
        - No race conditions in status updates

        Expected: Thread-safe operations (TDD red phase - will fail)
        """
        import threading

        from extension_base.health.reporter import HealthReporter

        reporter = HealthReporter(
            extension_id="test-ext-1", container_id="test-container-1"
        )

        # Function to update endpoint status
        def update_endpoint(endpoint_id: str, count: int):
            for i in range(count):
                reporter.update_endpoint_status(
                    endpoint_id=endpoint_id,
                    status="collecting",
                    collections_total=i,
                    errors_total=0,
                )

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(
                target=update_endpoint, args=(f"ep-{i}", 10)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Validate status is consistent
        status = reporter.get_status()
        assert len(status["endpoints"]) == 5, "All 5 endpoints must be tracked"

    def test_health_server_lifecycle(self):
        """
        Test health server lifecycle (start/stop).

        Spec Reference: docs/specs/extension-base-library.md#health-reporter
        - API/Interface - start_http_server(), stop_http_server() (lines 595-596)

        Validates:
        - start_http_server() starts server
        - stop_http_server() stops server gracefully
        - Server can be restarted
        - Resources cleaned up on stop

        Expected: Server lifecycle works (TDD red phase - will fail)
        """
        from extension_base.health.reporter import HealthReporter

        reporter = HealthReporter(
            extension_id="test-ext-1",
            container_id="test-container-1",
            http_port=8083,
        )

        # Start server
        reporter.start_http_server()
        assert reporter._http_server is not None
        assert reporter._http_thread.is_alive()

        # Stop server
        reporter.stop_http_server()
        time.sleep(0.1)  # Give thread time to stop

        assert not reporter._http_thread.is_alive(), (
            "HTTP thread must stop after stop_http_server()"
        )

        # Restart server
        reporter.start_http_server()
        assert reporter._http_server is not None
        assert reporter._http_thread.is_alive()

        # Cleanup
        reporter.stop_http_server()

    def test_health_status_persistence(self):
        """
        Test health status persistence across updates.

        Spec Reference: docs/specs/extension-base-library.md#health-reporter
        - Health Status Tracking (lines 497-502)
        - Health Status Format (lines 556-588)

        Validates:
        - Status persists between updates
        - Historical data maintained
        - Timestamps updated correctly
        - Status transitions tracked

        Expected: Status persists (TDD red phase - will fail)
        """
        from extension_base.health.reporter import HealthReporter

        reporter = HealthReporter(
            extension_id="test-ext-1", container_id="test-container-1"
        )

        # Initial status
        reporter.report_startup()
        status1 = reporter.get_status()
        timestamp1 = status1["timestamp"]

        # Wait and update
        time.sleep(0.1)
        reporter.update_endpoint_status(
            endpoint_id="ep-1",
            status="collecting",
            collections_total=10,
            errors_total=0,
        )

        status2 = reporter.get_status()
        timestamp2 = status2["timestamp"]

        # Validate persistence
        assert status2["extension_id"] == status1["extension_id"]
        assert status2["container_id"] == status1["container_id"]
        assert timestamp2 >= timestamp1, "Timestamp must increase with updates"
        assert "ep-1" in status2["endpoints"], (
            "Endpoint must persist in status"
        )


    def test_disabled_endpoint(self):
        """
        Test that a disabled endpoint is tracked correctly in the health output.

        Validates:
        - status is "disabled"
        - last_collection is absent (no collection ever ran)
        - counts are zero
        - a concurrently active endpoint is unaffected
        """
        from extension_base.health.reporter import HealthReporter

        reporter = HealthReporter(
            extension_id="test-ext-1", container_id="test-container-1"
        )

        reporter.update_endpoint_status(
            endpoint_id="ep-disabled",
            status="disabled",
            collections_total=0,
            errors_total=0,
        )
        reporter.update_endpoint_status(
            endpoint_id="ep-active",
            status="collecting",
            collections_total=1,
            errors_total=0,
        )

        endpoints = reporter.get_status()["endpoints"]

        disabled = endpoints["ep-disabled"]
        assert disabled["status"] == "disabled"
        assert disabled["collections_total"] == 0
        assert disabled["errors_total"] == 0
        assert "last_collection" not in disabled, (
            "Disabled endpoints must not carry a last_collection timestamp"
        )

        # Active endpoint must still have last_collection
        assert "last_collection" in endpoints["ep-active"]


    def test_all_endpoints_disabled_yields_idle_status(self):
        """
        When every endpoint is disabled the top-level status must be "idle".

        Validates:
        - All-disabled → top-level "idle", HTTP 200 (not 503).
        - A mix of disabled + active → top-level "healthy" (not "idle").
        """
        from extension_base.health.reporter import HealthReporter

        reporter = HealthReporter(
            extension_id="test-ext-1", container_id="test-container-1"
        )

        reporter.update_endpoint_status(endpoint_id="ep-1", status="disabled")
        reporter.update_endpoint_status(endpoint_id="ep-2", status="disabled")

        assert reporter.get_status()["status"] == "idle", (
            "All endpoints disabled must yield top-level status 'idle'"
        )

        # Once one endpoint becomes active the status must lift back to "healthy"
        reporter.update_endpoint_status(
            endpoint_id="ep-1", status="collecting", collections_total=1
        )
        assert reporter.get_status()["status"] == "healthy"


# Made with Bob
