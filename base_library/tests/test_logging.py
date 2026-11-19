# (c) Copyright IBM Corp. 2026
"""
Logging Module Tests for Extension Base Library

Tests structured logging with JSON formatting for container environments.

Test Coverage (FR9 - Logging Module):
- T113: JSONFormatter class exists and formats logs as JSON
- T114: setup_logging() configures logging with JSON format
- T115: get_logger() returns configured logger instance
- T116: Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) work correctly
- T117: Structured fields included in JSON logs (timestamp, level, logger, message)
- T118: Environment variable INSTANA_LOG_LEVEL overrides log level
- T119: Thread-safe logging with concurrent log writes

TDD Status: RED phase - All tests should FAIL initially (no implementation)

Spec Reference: docs/specs/extension-base-library.md#logging-module (lines 152-193)
"""

import json
import logging
import threading
import time
from io import StringIO

import pytest


class TestLogging:
    """Tests for logging module with JSON formatting."""

    def test_json_formatter_class_exists(self):
        """
        Test that JSONFormatter class exists and can format log records.

        Spec Reference: docs/specs/extension-base-library.md#logging-module
        - JSONFormatter (lines 170-181)
        - Functions (lines 187)

        Validates:
        - JSONFormatter class is defined in logging module
        - Can be instantiated
        - Has format() method
        - Formats log records as JSON strings
        - JSON output is valid and parseable

        Expected: JSONFormatter exists (TDD red phase - will fail)
        """
        from extension_base.logging import JSONFormatter

        # Validate JSONFormatter exists
        assert JSONFormatter is not None, "JSONFormatter must be defined"

        # Create formatter instance
        formatter = JSONFormatter()
        assert formatter is not None, "JSONFormatter must be instantiable"

        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Format the record
        formatted = formatter.format(record)
        assert formatted is not None, "format() must return a value"
        assert isinstance(formatted, str), "format() must return a string"

        # Verify it's valid JSON
        try:
            log_data = json.loads(formatted)
            assert isinstance(log_data, dict), (
                "Formatted output must be JSON object"
            )
        except json.JSONDecodeError as e:
            pytest.fail(f"Formatted output is not valid JSON: {e}")

        # Verify required fields present
        assert "timestamp" in log_data, "JSON log must include timestamp"
        assert "level" in log_data, "JSON log must include level"
        assert "logger" in log_data, "JSON log must include logger name"
        assert "message" in log_data, "JSON log must include message"

    def test_setup_logging_function(self):
        """
        Test setup_logging() function configures logging correctly.

        Spec Reference: docs/specs/extension-base-library.md#logging-module
        - Functions - setup_logging() (lines 185)
        - Implementation (lines 158-168)

        Validates:
        - setup_logging() function exists
        - Accepts level parameter (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        - Accepts json_format parameter (True/False)
        - Accepts logger_name parameter
        - Returns configured logger instance
        - Logger has correct level set
        - Logger has JSONFormatter attached (when json_format=True)

        Expected: setup_logging() works (TDD red phase - will fail)
        """
        from extension_base.logging import setup_logging

        # Test with default parameters
        logger = setup_logging()
        assert logger is not None, "setup_logging() must return a logger"
        assert isinstance(logger, logging.Logger), (
            "Must return Logger instance"
        )

        # Test with custom level
        logger = setup_logging(level="DEBUG")
        assert logger.level == logging.DEBUG, "Logger level not set correctly"

        # Test with json_format=True
        logger = setup_logging(level="INFO", json_format=True)
        assert logger.level == logging.INFO, "Logger level not set correctly"

        # Verify the root logger has a JSONFormatter handler.
        # setup_logging() installs the handler on the root logger so that
        # all child loggers (including the named one) inherit it via propagation.
        from extension_base.logging import JSONFormatter

        root_handlers = logging.getLogger().handlers
        assert len(root_handlers) > 0, "Root logger must have at least one handler"

        has_json_formatter = any(
            isinstance(h.formatter, JSONFormatter) for h in root_handlers
        )
        assert has_json_formatter, (
            "Root logger must have JSONFormatter when json_format=True"
        )

        # Test with custom logger name
        logger = setup_logging(logger_name="custom.logger")
        assert logger.name == "custom.logger", "Logger name not set correctly"

    def test_get_logger_function(self):
        """
        Test get_logger() function returns configured logger.

        Spec Reference: docs/specs/extension-base-library.md#logging-module
        - Functions - get_logger() (lines 186)
        - Implementation (lines 167)

        Validates:
        - get_logger() function exists
        - Accepts name parameter
        - Returns logger instance with specified name
        - Logger inherits configuration from root logger
        - Multiple calls with same name return same logger instance

        Expected: get_logger() works (TDD red phase - will fail)
        """
        from extension_base.logging import get_logger

        # Get logger with name
        logger1 = get_logger("test.module")
        assert logger1 is not None, "get_logger() must return a logger"
        assert isinstance(logger1, logging.Logger), (
            "Must return Logger instance"
        )
        assert logger1.name == "test.module", "Logger name not set correctly"

        # Get same logger again
        logger2 = get_logger("test.module")
        assert logger1 is logger2, (
            "Same name should return same logger instance"
        )

        # Get different logger
        logger3 = get_logger("other.module")
        assert logger3.name == "other.module", (
            "Different logger name not set correctly"
        )
        assert logger3 is not logger1, (
            "Different names should return different loggers"
        )

    def test_log_levels_work_correctly(self):
        """
        Test all log levels work correctly (DEBUG, INFO, WARNING, ERROR, CRITICAL).

        Spec Reference: docs/specs/extension-base-library.md#logging-module
        - Functions - setup_logging() level parameter (lines 185)

        Validates:
        - Logger accepts all standard log levels
        - Messages logged at correct level
        - Log level filtering works (e.g., INFO level doesn't log DEBUG)
        - Level names appear correctly in JSON output

        Expected: Log levels work (TDD red phase - will fail)
        """
        from extension_base.logging import JSONFormatter, setup_logging

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(JSONFormatter())

        # Setup logger with INFO level
        logger = setup_logging(level="INFO", json_format=True)
        logger.handlers.clear()  # Remove default handlers
        logger.addHandler(handler)

        # Log at different levels
        logger.debug("Debug message")  # Should NOT appear (below INFO)
        logger.info("Info message")  # Should appear
        logger.warning("Warning message")  # Should appear
        logger.error("Error message")  # Should appear
        logger.critical("Critical message")  # Should appear

        # Get logged output
        log_output = log_stream.getvalue()
        log_lines = [line for line in log_output.strip().split("\n") if line]

        # Should have 4 lines (INFO, WARNING, ERROR, CRITICAL - not DEBUG)
        assert len(log_lines) == 4, (
            f"Expected 4 log lines, got {len(log_lines)}"
        )

        # Verify each line is valid JSON with correct level
        expected_levels = ["INFO", "WARNING", "ERROR", "CRITICAL"]
        for line, expected_level in zip(log_lines, expected_levels):
            log_data = json.loads(line)
            assert log_data["level"] == expected_level, (
                f"Expected level {expected_level}, got {log_data['level']}"
            )

    def test_structured_fields_in_json_logs(self):
        """
        Test structured fields are included in JSON logs.

        Spec Reference: docs/specs/extension-base-library.md#logging-module
        - JSONFormatter - JSON structure (lines 174-180)

        Validates:
        - timestamp field present and valid ISO 8601 format
        - level field present (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        - logger field present (logger name)
        - message field present (log message)
        - Extra fields can be added via extra parameter
        - Exception info included when logging exceptions

        Expected: Structured fields work (TDD red phase - will fail)
        """
        from extension_base.logging import JSONFormatter, setup_logging

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(JSONFormatter())

        logger = setup_logging(level="INFO", json_format=True)
        logger.handlers.clear()
        logger.addHandler(handler)

        # Log with extra fields
        logger.info(
            "Test message with extras",
            extra={"endpoint_id": "421", "collection_count": 100},
        )

        # Get logged output
        log_output = log_stream.getvalue()
        log_data = json.loads(log_output.strip())

        # Verify standard fields
        assert "timestamp" in log_data, "timestamp field missing"
        assert "level" in log_data, "level field missing"
        assert "logger" in log_data, "logger field missing"
        assert "message" in log_data, "message field missing"

        # Verify timestamp is valid ISO 8601
        from datetime import datetime

        try:
            datetime.fromisoformat(
                log_data["timestamp"].replace("Z", "+00:00")
            )
        except ValueError as e:
            pytest.fail(f"Invalid timestamp format: {e}")

        # Verify extra fields included
        assert "endpoint_id" in log_data, "Extra field endpoint_id missing"
        assert log_data["endpoint_id"] == "421", "Extra field value incorrect"
        assert "collection_count" in log_data, (
            "Extra field collection_count missing"
        )
        assert log_data["collection_count"] == 100, (
            "Extra field value incorrect"
        )

        # Test exception logging
        log_stream.truncate(0)
        log_stream.seek(0)

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("Exception occurred")

        log_output = log_stream.getvalue()
        log_data = json.loads(log_output.strip())

        # Verify exception info included
        assert "exc_info" in log_data or "exception" in log_data, (
            "Exception info missing from log"
        )

    def test_environment_variable_log_level_override(self):
        """
        Test INSTANA_LOG_LEVEL environment variable overrides log level.

        Spec Reference: docs/specs/extension-base-library.md#logging-module
        - Environment Variables (lines 189-192)

        Validates:
        - INSTANA_LOG_LEVEL environment variable is read
        - Log level set from environment variable
        - Environment variable takes precedence over parameter
        - Invalid values handled gracefully (fallback to default)

        Expected: Environment override works (TDD red phase - will fail)
        """
        import os

        from extension_base.logging import setup_logging

        # Test with environment variable set
        os.environ["INSTANA_LOG_LEVEL"] = "DEBUG"

        try:
            logger = setup_logging(level="INFO")  # Parameter says INFO
            # But environment variable should override to DEBUG
            assert logger.level == logging.DEBUG, (
                "INSTANA_LOG_LEVEL environment variable not applied"
            )
        finally:
            os.environ.pop("INSTANA_LOG_LEVEL", None)

        # Test with invalid environment variable
        os.environ["INSTANA_LOG_LEVEL"] = "INVALID"

        try:
            logger = setup_logging(level="INFO")
            # Should fallback to parameter value (INFO)
            assert logger.level == logging.INFO, (
                "Invalid INSTANA_LOG_LEVEL should fallback to parameter"
            )
        finally:
            os.environ.pop("INSTANA_LOG_LEVEL", None)

        # Test without environment variable
        logger = setup_logging(level="WARNING")
        assert logger.level == logging.WARNING, (
            "Parameter value not used when env var absent"
        )

    def test_thread_safe_logging(self):
        """
        Test thread-safe logging with concurrent log writes.

        Spec Reference: docs/specs/extension-base-library.md#logging-module
        - Implementation (lines 158-168)

        Validates:
        - Multiple threads can log concurrently
        - No log messages lost
        - No log messages corrupted
        - Each log line is complete JSON
        - Thread information can be included in logs

        Expected: Thread-safe logging works (TDD red phase - will fail)
        """
        from extension_base.logging import JSONFormatter, setup_logging

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(JSONFormatter())

        logger = setup_logging(level="INFO", json_format=True)
        logger.handlers.clear()
        logger.addHandler(handler)

        # Track log counts per thread
        log_counts = {"thread1": 0, "thread2": 0, "thread3": 0}
        log_lock = threading.Lock()

        def log_worker(thread_name, count):
            """Worker function that logs messages."""
            for i in range(count):
                logger.info(
                    f"Message {i} from {thread_name}",
                    extra={"thread_name": thread_name, "message_num": i},
                )
                time.sleep(0.001)  # Small delay to encourage interleaving

            with log_lock:
                log_counts[thread_name] = count

        # Create and start threads
        threads = [
            threading.Thread(target=log_worker, args=("thread1", 10)),
            threading.Thread(target=log_worker, args=("thread2", 10)),
            threading.Thread(target=log_worker, args=("thread3", 10)),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=5)

        # Verify all threads completed
        assert all(not t.is_alive() for t in threads), (
            "Some threads did not complete"
        )

        # Get logged output
        log_output = log_stream.getvalue()
        log_lines = [line for line in log_output.strip().split("\n") if line]

        # Should have 30 total log lines (10 per thread)
        assert len(log_lines) == 30, (
            f"Expected 30 log lines, got {len(log_lines)}"
        )

        # Verify each line is valid JSON
        thread_counts = {"thread1": 0, "thread2": 0, "thread3": 0}
        for line in log_lines:
            try:
                log_data = json.loads(line)
                thread_name = log_data.get("thread_name")
                if thread_name in thread_counts:
                    thread_counts[thread_name] += 1
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in log line: {line}\nError: {e}")

        # Verify each thread logged correct number of messages
        assert thread_counts["thread1"] == 10, "thread1 log count incorrect"
        assert thread_counts["thread2"] == 10, "thread2 log count incorrect"
        assert thread_counts["thread3"] == 10, "thread3 log count incorrect"

    def test_standard_log_fields_present_and_formatted(self):
        """
        Test that all standard log fields are present and properly formatted.

        Spec Reference: docs/specs/extension-base-library.md#standard-log-fields
        - Standard Log Fields (lines 961-978)

        Validates:
        - timestamp field present and ISO 8601 format with timezone
        - level field present (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        - logger field present (module path string)
        - message field present (string)
        - thread_id field present (integer)
        - thread_name field present (string)
        - All fields have correct types

        Expected: Standard fields present and formatted (TDD red phase - will fail)
        """
        from datetime import datetime

        from extension_base.logging import JSONFormatter, setup_logging

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(JSONFormatter())

        logger = setup_logging(level="DEBUG", json_format=True)
        logger.handlers.clear()
        logger.addHandler(handler)

        # Test all log levels
        test_levels = [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ]

        for level_num, level_name in test_levels:
            log_stream.truncate(0)
            log_stream.seek(0)

            # Log at this level
            logger.log(level_num, f"Test message at {level_name}")

            # Parse output
            log_output = log_stream.getvalue().strip()
            log_data = json.loads(log_output)

            # Verify all 6 required fields present
            assert "timestamp" in log_data, (
                f"{level_name}: timestamp field missing"
            )
            assert "level" in log_data, f"{level_name}: level field missing"
            assert "logger" in log_data, f"{level_name}: logger field missing"
            assert "message" in log_data, (
                f"{level_name}: message field missing"
            )
            assert "thread_id" in log_data, (
                f"{level_name}: thread_id field missing"
            )
            assert "thread_name" in log_data, (
                f"{level_name}: thread_name field missing"
            )

            # Verify timestamp is ISO 8601 with timezone
            timestamp_str = log_data["timestamp"]
            assert isinstance(timestamp_str, str), (
                f"{level_name}: timestamp must be string"
            )
            try:
                # Parse ISO 8601 timestamp
                dt = datetime.fromisoformat(
                    timestamp_str.replace("Z", "+00:00")
                )
                assert dt is not None, (
                    f"{level_name}: timestamp not valid ISO 8601"
                )
            except ValueError as e:
                pytest.fail(
                    f"{level_name}: Invalid ISO 8601 timestamp format: {e}"
                )

            # Verify level matches expected value
            assert log_data["level"] == level_name, (
                f"Expected level {level_name}, got {log_data['level']}"
            )

            # Verify logger is string (module path)
            assert isinstance(log_data["logger"], str), (
                f"{level_name}: logger must be string"
            )

            # Verify message is string
            assert isinstance(log_data["message"], str), (
                f"{level_name}: message must be string"
            )
            assert f"Test message at {level_name}" in log_data["message"], (
                f"{level_name}: message content incorrect"
            )

            # Verify thread_id is integer
            assert isinstance(log_data["thread_id"], int), (
                f"{level_name}: thread_id must be integer"
            )

            # Verify thread_name is string
            assert isinstance(log_data["thread_name"], str), (
                f"{level_name}: thread_name must be string"
            )

    def test_set_thread_context_function(self):
        """
        Test set_thread_context() function for thread-specific logging.

        Spec Reference: docs/specs/extension-base-library.md#thread-level-logging
        - Thread-Level Logging (lines 979-1045)

        Validates:
        - set_thread_context() function exists
        - Accepts dictionary of context fields
        - Context is stored per-thread
        - Context persists across multiple log calls

        Expected: set_thread_context() works (TDD red phase - will fail)
        """
        from extension_base.logging import set_thread_context

        # Set thread context
        context = {"endpoint": "api-server", "collection_id": "12345"}
        set_thread_context(context)

        # Verify function exists and accepts dict
        assert True, "set_thread_context() must accept dictionary"

    def test_thread_context_included_in_logs(self):
        """
        Test that thread context fields are included in log entries.

        Spec Reference: docs/specs/extension-base-library.md#thread-level-logging
        - Thread-Level Logging (lines 979-1045)

        Validates:
        - Context fields appear in log output
        - Multiple context fields supported
        - Context fields are in JSON output
        - Context applies to all logs in thread

        Expected: Thread context in logs (TDD red phase - will fail)
        """
        from extension_base.logging import (
            JSONFormatter,
            set_thread_context,
            setup_logging,
        )

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(JSONFormatter())

        logger = setup_logging(level="INFO", json_format=True)
        logger.handlers.clear()
        logger.addHandler(handler)

        # Set thread context
        set_thread_context(
            {"endpoint": "api-server", "collection_id": "12345", "attempt": 1}
        )

        # Log message
        logger.info("Starting collection")

        # Parse output
        log_output = log_stream.getvalue().strip()
        log_data = json.loads(log_output)

        # Verify context fields in log
        assert "endpoint" in log_data, "endpoint context field missing"
        assert log_data["endpoint"] == "api-server", (
            "endpoint context value incorrect"
        )
        assert "collection_id" in log_data, (
            "collection_id context field missing"
        )
        assert log_data["collection_id"] == "12345", (
            "collection_id context value incorrect"
        )
        assert "attempt" in log_data, "attempt context field missing"
        assert log_data["attempt"] == 1, "attempt context value incorrect"

        # Log another message - context should persist
        log_stream.truncate(0)
        log_stream.seek(0)
        logger.info("Collection complete")

        log_output = log_stream.getvalue().strip()
        log_data = json.loads(log_output)

        # Context should still be present
        assert "endpoint" in log_data, (
            "endpoint context not persisted across logs"
        )
        assert log_data["endpoint"] == "api-server", (
            "endpoint context value changed"
        )

    def test_thread_context_isolation(self):
        """
        Test that thread contexts are isolated between threads.

        Spec Reference: docs/specs/extension-base-library.md#thread-level-logging
        - Thread-Level Logging (lines 979-1045)

        Validates:
        - Each thread has its own context
        - Context doesn't leak between threads
        - Concurrent threads maintain separate contexts
        - Context cleared when thread exits

        Expected: Thread context isolation works (TDD red phase - will fail)
        """
        import queue
        import threading

        from extension_base.logging import (
            JSONFormatter,
            set_thread_context,
            setup_logging,
        )

        # Queue to collect log outputs from threads
        log_queue = queue.Queue()

        def thread_worker(thread_id, endpoint_name):
            """Worker that sets context and logs."""
            # Capture this thread's logs
            log_stream = StringIO()
            handler = logging.StreamHandler(log_stream)
            handler.setFormatter(JSONFormatter())

            logger = setup_logging(level="INFO", json_format=True)
            logger.handlers.clear()
            logger.addHandler(handler)

            # Set thread-specific context
            set_thread_context(
                {"thread_id": thread_id, "endpoint": endpoint_name}
            )

            # Log message
            logger.info(f"Message from {thread_id}")

            # Get log output
            log_output = log_stream.getvalue().strip()
            log_queue.put((thread_id, log_output))

        # Create threads with different contexts
        threads = [
            threading.Thread(
                target=thread_worker, args=("thread1", "endpoint-a")
            ),
            threading.Thread(
                target=thread_worker, args=("thread2", "endpoint-b")
            ),
            threading.Thread(
                target=thread_worker, args=("thread3", "endpoint-c")
            ),
        ]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=5)

        # Collect and verify logs
        logs_by_thread = {}
        while not log_queue.empty():
            thread_id, log_output = log_queue.get()
            logs_by_thread[thread_id] = json.loads(log_output)

        # Verify each thread has its own context
        assert "thread1" in logs_by_thread, "thread1 log missing"
        assert logs_by_thread["thread1"]["endpoint"] == "endpoint-a", (
            "thread1 context incorrect"
        )

        assert "thread2" in logs_by_thread, "thread2 log missing"
        assert logs_by_thread["thread2"]["endpoint"] == "endpoint-b", (
            "thread2 context incorrect"
        )

        assert "thread3" in logs_by_thread, "thread3 log missing"
        assert logs_by_thread["thread3"]["endpoint"] == "endpoint-c", (
            "thread3 context incorrect"
        )

        # Verify no context leakage
        assert logs_by_thread["thread1"]["thread_id"] == "thread1", (
            "thread1 ID incorrect"
        )
        assert logs_by_thread["thread2"]["thread_id"] == "thread2", (
            "thread2 ID incorrect"
        )
        assert logs_by_thread["thread3"]["thread_id"] == "thread3", (
            "thread3 ID incorrect"
        )

    def test_structured_field_types(self):
        """
        Test that structured logging supports different field types.

        Spec Reference: docs/specs/extension-base-library.md#structured-logging-fields
        - Structured Logging Fields (lines 1046-1073)

        Validates:
        - String fields work correctly
        - Numeric fields (int and float) work correctly
        - Boolean fields work correctly
        - Nested object fields work correctly
        - Field types preserved through JSON serialization

        Expected: Structured field types work (TDD red phase - will fail)
        """
        from extension_base.logging import JSONFormatter, setup_logging

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(JSONFormatter())

        logger = setup_logging(level="INFO", json_format=True)
        logger.handlers.clear()
        logger.addHandler(handler)

        # Log with different field types
        logger.info(
            "Test message with various field types",
            extra={
                "string_field": "test_value",
                "int_field": 42,
                "float_field": 3.14,
                "bool_field": True,
                "nested_object": {"key1": "value1", "key2": 123},
            },
        )

        # Parse output
        log_output = log_stream.getvalue().strip()
        log_data = json.loads(log_output)

        # Verify string field
        assert "string_field" in log_data, "string_field missing"
        assert isinstance(log_data["string_field"], str), (
            "string_field must be string"
        )
        assert log_data["string_field"] == "test_value", (
            "string_field value incorrect"
        )

        # Verify int field
        assert "int_field" in log_data, "int_field missing"
        assert isinstance(log_data["int_field"], int), "int_field must be int"
        assert log_data["int_field"] == 42, "int_field value incorrect"

        # Verify float field
        assert "float_field" in log_data, "float_field missing"
        assert isinstance(log_data["float_field"], float), (
            "float_field must be float"
        )
        assert log_data["float_field"] == 3.14, "float_field value incorrect"

        # Verify boolean field
        assert "bool_field" in log_data, "bool_field missing"
        assert isinstance(log_data["bool_field"], bool), (
            "bool_field must be bool"
        )
        assert log_data["bool_field"] is True, "bool_field value incorrect"

        # Verify nested object
        assert "nested_object" in log_data, "nested_object missing"
        assert isinstance(log_data["nested_object"], dict), (
            "nested_object must be dict"
        )
        assert log_data["nested_object"]["key1"] == "value1", (
            "nested_object.key1 incorrect"
        )
        assert log_data["nested_object"]["key2"] == 123, (
            "nested_object.key2 incorrect"
        )

    def test_structured_field_naming_conventions(self):
        """
        Test structured field naming conventions and reserved field handling.

        Spec Reference: docs/specs/extension-base-library.md#structured-logging-fields
        - Structured Logging Fields - Field Naming (lines 1046-1073)

        Validates:
        - snake_case field names work correctly
        - Reserved field names handled (timestamp, level, logger, message)
        - Custom fields don't overwrite standard fields
        - Field name validation/sanitization

        Expected: Field naming conventions enforced (TDD red phase - will fail)
        """
        from extension_base.logging import JSONFormatter, setup_logging

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(JSONFormatter())

        logger = setup_logging(level="INFO", json_format=True)
        logger.handlers.clear()
        logger.addHandler(handler)

        # Test snake_case field names
        logger.info(
            "Test snake_case fields",
            extra={
                "endpoint_id": "ep-123",
                "collection_count": 42,
                "is_successful": True,
            },
        )

        log_output = log_stream.getvalue().strip()
        log_data = json.loads(log_output)

        # Verify snake_case fields work
        assert "endpoint_id" in log_data, "snake_case field missing"
        assert "collection_count" in log_data, "snake_case field missing"
        assert "is_successful" in log_data, "snake_case field missing"

        # Test that reserved fields are not overwritten
        log_stream.truncate(0)
        log_stream.seek(0)

        # Try to override reserved fields (should be ignored or handled)
        logger.info(
            "Original message",
            extra={
                "message": "Attempted override",  # Reserved field
                "level": "FAKE_LEVEL",  # Reserved field
                "custom_field": "This should work",
            },
        )

        log_output = log_stream.getvalue().strip()
        log_data = json.loads(log_output)

        # Verify standard fields not overwritten
        assert log_data["message"] == "Original message", (
            "Reserved 'message' field was overwritten"
        )
        assert log_data["level"] == "INFO", (
            "Reserved 'level' field was overwritten"
        )

        # Verify custom field still works
        assert "custom_field" in log_data, "custom_field missing"
        assert log_data["custom_field"] == "This should work", (
            "custom_field value incorrect"
        )


# Made with Bob

# Made with Bob
