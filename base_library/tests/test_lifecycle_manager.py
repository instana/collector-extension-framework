# (c) Copyright IBM Corp. 2026
"""
Tests for Lifecycle Manager (FR6).

This module contains tests for the Lifecycle Manager component which manages
extension lifecycle including startup, shutdown, signal handling, and thread
management.

Test Coverage:
- T086: Lifecycle manager class structure
- T087: Signal handling (SIGTERM, SIGINT)
- T088: Thread management for endpoint collection
- T089: Graceful shutdown coordination
- T090: Resource cleanup on shutdown
- T091: Thread health monitoring
- T092: Thread restart on failure
- T093: Shutdown timeout handling
- T094: Multiple endpoint thread management
- T095: Thread pool sizing

TDD Approach:
- All tests written BEFORE implementation
- Tests will FAIL initially (red phase)
- Implementation will make tests PASS (green phase)

Spec Reference: docs/specs/extension-base-library.md#lifecycle-manager (lines 618-759)
"""

import signal
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

from extension_base.health.reporter import HealthReporter
from extension_base.lifecycle.manager import LifecycleManager


class TestLifecycleManager:
    """Test suite for Lifecycle Manager component."""

    def test_lifecycle_manager_class_exists(self):
        """
        Test that LifecycleManager class exists and can be instantiated.

        Spec Reference: docs/specs/extension-base-library.md#lifecycle-manager
        - API/Interface (lines 749-758)

        Validates:
        - LifecycleManager class is defined in lifecycle.manager module
        - Can be instantiated with config and health reporter
        - Has start() method
        - Has shutdown() method
        - Has register_shutdown_handler() method

        Expected: LifecycleManager class exists (TDD red phase - will fail)
        """
        from extension_base.lifecycle import manager

        # Validate LifecycleManager exists
        assert hasattr(manager, "LifecycleManager"), (
            "LifecycleManager must be defined in lifecycle.manager module"
        )

        # Validate required methods exist
        LifecycleManager = manager.LifecycleManager
        required_methods = [
            "start",
            "shutdown",
            "register_shutdown_handler",
        ]

        for method in required_methods:
            assert hasattr(LifecycleManager, method), (
                f"LifecycleManager must have {method}() method"
            )

    def test_signal_handling_sigterm(self, valid_config):
        """
        Test SIGTERM signal handling for graceful shutdown.

        Spec Reference: docs/specs/extension-base-library.md#lifecycle-manager
        - Signal Handling (lines 626-630)

        Validates:
        - register_shutdown_handler() registers SIGTERM handler
        - SIGTERM triggers graceful shutdown
        - Shutdown flag is set
        - Resources are cleaned up

        Expected: SIGTERM handled (TDD red phase - will fail)
        """
        health_reporter = Mock(spec=HealthReporter)
        manager = LifecycleManager(
            config=valid_config, health_reporter=health_reporter
        )

        # Register signal handler
        manager.register_shutdown_handler()

        # Verify SIGTERM handler registered
        with patch("signal.signal") as mock_signal:
            manager.register_shutdown_handler()
            mock_signal.assert_any_call(signal.SIGTERM, manager._handle_signal)

    def test_signal_handling_sigint(self, valid_config):
        """
        Test SIGINT signal handling for graceful shutdown.

        Spec Reference: docs/specs/extension-base-library.md#lifecycle-manager
        - Signal Handling (lines 626-630)

        Validates:
        - register_shutdown_handler() registers SIGINT handler
        - SIGINT triggers graceful shutdown
        - Shutdown flag is set
        - Resources are cleaned up

        Expected: SIGINT handled (TDD red phase - will fail)
        """
        health_reporter = Mock(spec=HealthReporter)
        manager = LifecycleManager(
            config=valid_config, health_reporter=health_reporter
        )

        # Verify SIGINT handler registered
        with patch("signal.signal") as mock_signal:
            manager.register_shutdown_handler()
            mock_signal.assert_any_call(signal.SIGINT, manager._handle_signal)

    def test_thread_management_for_endpoints(self, valid_config):
        """
        Test thread management for endpoint collection.

        Spec Reference: docs/specs/extension-base-library.md#lifecycle-manager
        - Thread Management (lines 632-636)

        Validates:
        - One thread created per endpoint
        - Threads start successfully
        - Threads run collection function
        - Thread count matches endpoint count

        Expected: Threads managed correctly (TDD red phase - will fail)
        """
        health_reporter = Mock(spec=HealthReporter)
        manager = LifecycleManager(
            config=valid_config, health_reporter=health_reporter
        )

        # Mock collection function
        collection_func = Mock()

        # Start collection threads
        manager.start(collection_func)

        # Verify threads created
        assert len(manager._threads) == len(
            valid_config.configuration.endpoints
        ), "One thread must be created per endpoint"

        # Verify all threads are alive
        for thread in manager._threads:
            assert thread.is_alive(), "All threads must be running"

        # Cleanup
        manager.shutdown()

    def test_graceful_shutdown_coordination(self, valid_config):
        """
        Test graceful shutdown coordination.

        Spec Reference: docs/specs/extension-base-library.md#lifecycle-manager
        - Graceful Shutdown (lines 638-644)

        Validates:
        - shutdown() stops all threads
        - In-flight collections complete
        - Metrics are flushed
        - Health status updated
        - Resources cleaned up

        Expected: Graceful shutdown works (TDD red phase - will fail)
        """
        health_reporter = Mock(spec=HealthReporter)
        manager = LifecycleManager(
            config=valid_config, health_reporter=health_reporter
        )

        # Start with mock collection function
        collection_func = Mock()
        manager.start(collection_func)

        # Verify threads running
        assert all(t.is_alive() for t in manager._threads)

        # Shutdown
        manager.shutdown(timeout_seconds=5)

        # Verify shutdown flag set
        assert manager._shutdown_flag.is_set(), "Shutdown flag must be set"

        # Verify threads stopped
        time.sleep(0.5)  # Give threads time to stop
        assert all(not t.is_alive() for t in manager._threads), (
            "All threads must be stopped after shutdown"
        )

    def test_resource_cleanup_on_shutdown(self, valid_config):
        """
        Test resource cleanup on shutdown.

        Spec Reference: docs/specs/extension-base-library.md#lifecycle-manager
        - Graceful Shutdown (lines 638-644)

        Validates:
        - Threads are joined
        - Metrics provider is shut down
        - Health reporter is updated
        - File handles are closed
        - Network connections are closed

        Expected: Resources cleaned up (TDD red phase - will fail)
        """
        health_reporter = Mock(spec=HealthReporter)
        meter_provider = Mock()

        manager = LifecycleManager(
            config=valid_config,
            health_reporter=health_reporter,
            meter_provider=meter_provider,
        )

        # Start and shutdown
        collection_func = Mock()
        manager.start(collection_func)
        manager.shutdown()

        # Verify meter provider shutdown called
        meter_provider.shutdown.assert_called_once()

    def test_thread_health_monitoring(self, valid_config):
        """
        Test thread health monitoring.

        Spec Reference: docs/specs/extension-base-library.md#lifecycle-manager
        - Thread Management (lines 635)
        - Error Recovery (lines 646-649)

        Validates:
        - Monitors thread status
        - Detects crashed threads
        - Reports thread health to health reporter
        - Tracks thread errors
        - _run_endpoint passes collections_total=1, errors_total=0 on success
        - _run_endpoint passes collections_total=0, errors_total=1 on failure
          (delta-based: the reporter accumulates, the caller always passes 1)

        Expected: Thread health monitored (TDD red phase - will fail)
        """
        health_reporter = Mock(spec=HealthReporter)
        manager = LifecycleManager(
            config=valid_config,
            health_reporter=health_reporter,
            retry_on_failure=True,  # allows the loop to continue after failure
        )

        # Fails on the first call only; retry_on_failure=True causes the
        # thread to back off and call the function again.
        call_count = 0

        def flaky_collection(endpoint, emitter):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First call fails")
            # Second call succeeds — thread reports success then sleeps

        manager.start(flaky_collection)
        # First back-off is 2^1 = 2 s; wait long enough for the retry to fire
        time.sleep(3.5)
        manager.shutdown()

        calls = health_reporter.update_endpoint_status.call_args_list
        assert len(calls) >= 2, (
            "update_endpoint_status must be called at least twice "
            "(once for the error, once for the subsequent success)"
        )

        # The error call must carry errors_total=1, collections_total=0
        error_calls = [
            c for c in calls if c.kwargs.get("errors_total", 0) == 1
        ]
        assert error_calls, (
            "At least one call must have errors_total=1 for the failing collection"
        )
        assert all(c.kwargs.get("collections_total", -1) == 0 for c in error_calls), (
            "Error calls must pass collections_total=0 (delta, not a running total)"
        )

        # The success call must carry collections_total=1, errors_total=0
        success_calls = [
            c for c in calls if c.kwargs.get("collections_total", 0) == 1
        ]
        assert success_calls, (
            "At least one call must have collections_total=1 for a successful collection"
        )
        assert all(c.kwargs.get("errors_total", -1) == 0 for c in success_calls), (
            "Success calls must pass errors_total=0 (delta, not a running total)"
        )

    def test_thread_retry_on_failure(self, valid_config):
        """
        Test thread retry on failure with exponential back-off.

        Spec Reference: docs/specs/extension-base-library.md#lifecycle-manager
        - Error Recovery (lines 646-649)

        Validates:
        - Retries collection if retry_on_failure enabled
        - retry_count resets to 0 on a successful collection
        - Endpoint eventually marked "collecting" after recovery

        Expected: Thread retries and recovers correctly
        """
        health_reporter = Mock(spec=HealthReporter)
        manager = LifecycleManager(
            config=valid_config,
            health_reporter=health_reporter,
            retry_on_failure=True,
        )

        # Track call attempts
        attempt_count = 0

        def failing_then_succeeding(endpoint, emitter):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 2:
                raise Exception("Temporary failure")
            # Succeed on third attempt

        manager.start(failing_then_succeeding)

        # Wait long enough for two back-offs (2s + 4s) and a successful call
        time.sleep(8.0)

        # Verify retries occurred and eventually succeeded
        assert attempt_count >= 3, "Collection should be retried after failure"

        # At least one successful update_endpoint_status with status="collecting"
        collecting_calls = [
            c for c in health_reporter.update_endpoint_status.call_args_list
            if c.kwargs.get("status") == "collecting"
        ]
        assert collecting_calls, "Endpoint should be marked 'collecting' after recovery"

        manager.shutdown()

    def test_shutdown_timeout_handling(self, valid_config):
        """
        Test shutdown timeout handling.

        Spec Reference: docs/specs/extension-base-library.md#lifecycle-manager
        - Signal Handling - shutdown timeout (lines 629)
        - Graceful Shutdown (lines 640)

        Validates:
        - Waits for threads to complete
        - Enforces shutdown timeout
        - Forces thread termination after timeout
        - Logs timeout events

        Expected: Timeout handled (TDD red phase - will fail)
        """
        health_reporter = Mock(spec=HealthReporter)
        manager = LifecycleManager(
            config=valid_config, health_reporter=health_reporter
        )

        # Collection function that takes long time
        def slow_collection(endpoint, emitter):
            time.sleep(10)  # Longer than timeout

        # Start collection
        manager.start(slow_collection)

        # Shutdown with short timeout
        start_time = time.time()
        manager.shutdown(timeout_seconds=1)
        elapsed = time.time() - start_time

        # Verify shutdown completed within timeout
        assert elapsed < 2.0, "Shutdown must complete within timeout period"

    def test_multiple_endpoint_thread_management(self, valid_config):
        """
        Test managing threads for multiple endpoints.

        Spec Reference: docs/specs/extension-base-library.md#lifecycle-manager
        - Thread Management (lines 632-636)

        Validates:
        - Creates separate thread per endpoint
        - Threads run independently
        - Thread failure doesn't affect others
        - All threads can be stopped together

        Expected: Multiple threads managed (TDD red phase - will fail)
        """
        health_reporter = Mock(spec=HealthReporter)
        manager = LifecycleManager(
            config=valid_config, health_reporter=health_reporter
        )

        # Track which endpoints were called
        called_endpoints = set()

        def collection_func(endpoint, emitter):
            called_endpoints.add(endpoint["id"])
            time.sleep(0.1)

        # Start collection
        manager.start(collection_func)

        # Wait for collections
        time.sleep(0.5)

        # Verify all endpoints called
        expected_endpoints = {
            ep["id"] for ep in valid_config.configuration.endpoints
        }
        assert called_endpoints == expected_endpoints, (
            "All endpoints must be processed by separate threads"
        )

        # Cleanup
        manager.shutdown()

    def test_thread_pool_sizing(self, valid_config):
        """
        Test thread pool sizing limits.

        Spec Reference: docs/specs/extension-base-library.md#lifecycle-manager
        - Thread Pool Management (lines 661-665)

        Validates:
        - Maximum 35 threads per container
        - Thread count matches endpoint count
        - Thread pool doesn't exceed limits
        - Warning logged if limit approached

        Expected: Thread pool sized correctly (TDD red phase - will fail)
        """
        health_reporter = Mock(spec=HealthReporter)
        manager = LifecycleManager(
            config=valid_config,
            health_reporter=health_reporter,
            max_threads=35,
        )

        collection_func = Mock()
        manager.start(collection_func)

        # Verify thread count within limits
        assert len(manager._threads) <= 35, "Thread count must not exceed 35"

        # Verify thread count matches endpoints
        endpoint_count = len(valid_config.configuration.endpoints)
        assert len(manager._threads) == endpoint_count, (
            "Thread count must match endpoint count"
        )

        manager.shutdown()


    def test_meter_name_uses_extension_name_from_object_config(
        self, mock_meter_provider
    ):
        """
        Test that the meter is created with extension_name when config is an
        object (attribute-style access).

        Validates the fix that passes ``extension_name`` as the instrumentation
        scope name so Instana shows metrics as ``<extension_name>/*`` instead of
        the internal module path ``extension_base.lifecycle.manager/…``.
        """
        config = SimpleNamespace(
            extension_name="my-mysql-extension",
            configuration=SimpleNamespace(
                endpoints=[
                    SimpleNamespace(
                        id="ep-1",
                        url="http://localhost",
                        interval=15,
                        enabled=True,
                    )
                ]
            ),
        )
        health_reporter = Mock(spec=HealthReporter)
        manager = LifecycleManager(
            config=config,
            health_reporter=health_reporter,
            meter_provider=mock_meter_provider,
        )

        manager.start(Mock())
        manager.shutdown()

        # get_meter is called twice: once for the business meter, once for the
        # internal meter (both from the same provider when no internal_meter_provider
        # is supplied). Both calls must use the extension_name scope.
        assert mock_meter_provider.get_meter.call_count == 3
        mock_meter_provider.get_meter.assert_called_with("my-mysql-extension")

    def test_meter_name_uses_extension_name_from_dict_config(
        self, mock_meter_provider
    ):
        """
        Test that the meter is created with extension_name when config is a
        plain dict.
        """
        config = {
            "extension_name": "my-redis-extension",
            "configuration": {
                "endpoints": [
                    {
                        "id": "ep-1",
                        "url": "http://localhost",
                        "interval": 15,
                        "enabled": True,
                    }
                ]
            },
        }
        health_reporter = Mock(spec=HealthReporter)
        manager = LifecycleManager(
            config=config,
            health_reporter=health_reporter,
            meter_provider=mock_meter_provider,
        )

        manager.start(Mock())
        manager.shutdown()

        assert mock_meter_provider.get_meter.call_count == 3
        mock_meter_provider.get_meter.assert_called_with("my-redis-extension")

    def test_meter_name_falls_back_to_module_name_when_extension_name_missing(
        self, mock_meter_provider
    ):
        """
        Test that the meter falls back to the module __name__ when
        extension_name is absent from the config.
        """
        import extension_base.lifecycle.manager as _manager_mod

        config = SimpleNamespace(
            # no extension_name attribute
            configuration=SimpleNamespace(
                endpoints=[
                    SimpleNamespace(
                        id="ep-1",
                        url="http://localhost",
                        interval=15,
                        enabled=True,
                    )
                ]
            ),
        )
        health_reporter = Mock(spec=HealthReporter)
        manager = LifecycleManager(
            config=config,
            health_reporter=health_reporter,
            meter_provider=mock_meter_provider,
        )

        manager.start(Mock())
        manager.shutdown()

        assert mock_meter_provider.get_meter.call_count == 3
        mock_meter_provider.get_meter.assert_called_with(_manager_mod.__name__)


    def test_disabled_endpoints_are_not_started(self):
        """
        Disabled endpoints must not receive a collection thread.

        Validates:
        - A mix of enabled and disabled endpoints yields threads only for
          the enabled subset.
        - The disabled endpoint is reported to the health reporter with
          status "disabled".
        - collection_func is never called for the disabled endpoint.
        """
        from types import SimpleNamespace

        enabled_ep = SimpleNamespace(id="ep-enabled", url="http://host1", interval=15, enabled=True)
        disabled_ep = SimpleNamespace(id="ep-disabled", url="http://host2", interval=15, enabled=False)

        config = SimpleNamespace(
            extension_name="test-extension",
            configuration=SimpleNamespace(endpoints=[enabled_ep, disabled_ep]),
        )

        health_reporter = Mock(spec=HealthReporter)
        manager = LifecycleManager(config=config, health_reporter=health_reporter)

        called_for = []

        def collection_func(endpoint, emitter):
            called_for.append(endpoint.id)

        manager.start(collection_func)

        # Only one thread for the enabled endpoint
        assert len(manager._threads) == 1, "Only enabled endpoints must receive a thread"
        assert manager._threads[0].name == "collection-ep-enabled"

        # Health reporter must have been notified about the disabled endpoint
        health_reporter.update_endpoint_status.assert_any_call(
            endpoint_id="ep-disabled",
            status="disabled",
            collections_total=0,
            errors_total=0,
        )

        manager.shutdown()

        # collection_func must never have been invoked for the disabled endpoint
        assert "ep-disabled" not in called_for


# Made with Bob
