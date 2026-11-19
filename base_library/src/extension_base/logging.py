# (c) Copyright IBM Corp. 2026
"""
Structured logging with JSON formatter for container environments.

Provides JSONFormatter, setup_logging(), get_logger(), and
set_thread_context() for consistent structured log output.
"""

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any

__all__ = [
    "JSONFormatter",
    "setup_logging",
    "get_logger",
    "set_thread_context",
]

# Reserved top-level fields that must not be overwritten by extra data.
_RESERVED_FIELDS = frozenset({"timestamp", "level", "logger", "message"})

# Fields that Python's logging.makeRecord protects (raises KeyError on clash).
_MAKERECORD_PROTECTED = frozenset({"message", "asctime"})

# Thread-local storage for per-thread context fields.
_thread_local = threading.local()


class ExtensionLogger(logging.Logger):
    """Logger subclass that silently drops reserved/protected keys from extra.

    Python's :meth:`logging.Logger.makeRecord` raises ``KeyError`` if
    ``extra`` contains ``"message"`` or any key already in the LogRecord
    ``__dict__``.  ExtensionLogger strips those keys before calling super
    so callers never see that exception.
    """

    def makeRecord(  # type: ignore[override]
        self,
        name,
        level,
        fn,
        lno,
        msg,
        args,
        exc_info,
        func=None,
        extra=None,
        sinfo=None,
    ):
        if extra:
            # Drop keys that collide with LogRecord's protected attrs so
            # super().makeRecord() does not raise KeyError.
            extra = {
                k: v
                for k, v in extra.items()
                if k not in _MAKERECORD_PROTECTED
            }
        return super().makeRecord(
            name, level, fn, lno, msg, args, exc_info, func, extra, sinfo
        )


def set_thread_context(context: dict[str, Any]) -> None:
    """Store *context* as thread-local fields included in every log record.

    Fields already stored are replaced by this call (full replacement).
    Context is isolated per thread — one thread cannot read another's context.

    Args:
        context: Mapping of field name → value to attach to log records.
    """
    _thread_local.context = dict(context)


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects.

    Standard fields emitted for every record:
        timestamp  – ISO 8601 UTC string (e.g. "2026-06-08T22:00:00.000000+00:00")
        level      – uppercase level name  (e.g. "INFO")
        logger     – logger name           (e.g. "extension_base.core")
        message    – formatted log message
        thread_id  – integer OS thread id
        thread_name – thread name string

    Additional fields come from:
        1. Thread context set via set_thread_context()
        2. The ``extra`` dict passed to the log call

    Reserved fields (timestamp, level, logger, message) from extra/context
    are silently dropped so they cannot overwrite standard fields.
    """

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        # Render the message (handles %-style formatting and exceptions)
        message = record.getMessage()

        record_dict: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "thread_id": record.thread,
            "thread_name": record.threadName,
        }

        # Merge thread-local context (skip reserved fields)
        thread_ctx: dict[str, Any] = getattr(_thread_local, "context", {})
        for key, value in thread_ctx.items():
            if key not in _RESERVED_FIELDS:
                record_dict[key] = value

        # Merge extra fields from the log call (skip reserved fields and
        # standard LogRecord attributes to avoid noise)
        _std_attrs = logging.LogRecord.__dict__.keys() | {
            "message",
            "asctime",
            "exc_text",
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED_FIELDS or key in _std_attrs or key.startswith("_"):
                continue
            # Only include fields explicitly added via extra={}
            # (i.e., not part of the standard LogRecord schema)
            if key not in {
                "name", "msg", "args", "levelname", "levelno",
                "pathname", "filename", "module", "exc_info",
                "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process",
                "stack_info", "lineno", "taskName",
            }:
                if key not in _RESERVED_FIELDS:
                    record_dict[key] = value

        # Append exception info if present
        if record.exc_info:
            record_dict["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(record_dict, default=str)


def setup_logging(
    level: str | None = "INFO",
    json_format: bool = True,
    logger_name: str = "extension_base",
) -> logging.Logger:
    """Configure the root logger and return a named child logger.

    Configures the **root** logger so that every logger in the process
    (extension code, library internals, third-party) inherits the handler
    and level via propagation.  Also configures the named *logger_name*
    logger for direct use by callers.

    The ``INSTANA_LOG_LEVEL`` environment variable takes precedence over
    the *level* parameter; invalid values fall back to *level*.

    Args:
        level: Default log level string (DEBUG / INFO / WARNING / ERROR /
               CRITICAL). Overridden by INSTANA_LOG_LEVEL env var.
        json_format: When True, attach a JSONFormatter to the handler.
        logger_name: Name of the child logger to return.

    Returns:
        Configured :class:`logging.Logger` instance for *logger_name*.
    """
    # Resolve effective level — env var wins over parameter
    level_name = level.upper() if isinstance(level, str) else "INFO"
    env_level = os.environ.get("INSTANA_LOG_LEVEL", "").upper()
    if env_level:
        numeric = getattr(logging, env_level, None)
        if isinstance(numeric, int):
            level_name = env_level
        # else: invalid env var → fall back to parameter

    numeric_level = getattr(logging, level_name, logging.INFO)

    # Configure the root logger — all other loggers propagate to it.
    root = logging.getLogger()
    root.setLevel(numeric_level)
    if not root.handlers:
        handler = logging.StreamHandler()
        if json_format:
            handler.setFormatter(JSONFormatter())
        root.addHandler(handler)
    elif json_format:
        for handler in root.handlers:
            handler.setFormatter(JSONFormatter())

    # Also retrieve/create the named logger and upgrade its class.
    logging.setLoggerClass(ExtensionLogger)
    logger = logging.getLogger(logger_name)
    logging.setLoggerClass(logging.Logger)  # restore default for other callers
    if not isinstance(logger, ExtensionLogger):
        logger.__class__ = ExtensionLogger
    logger.setLevel(numeric_level)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return the :class:`logging.Logger` with the given *name*.

    Repeated calls with the same name return the same instance (standard
    Python logging behaviour).

    Args:
        name: Logger name (typically the module's ``__name__``).

    Returns:
        :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)
