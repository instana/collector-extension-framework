#!/usr/bin/env python3
# (c) Copyright IBM Corp. 2026
"""
MySQL Collector Extension.

Connects to MySQL, queries SHOW GLOBAL STATUS, and emits OTel metrics via
the Extension Base Library.  Run as the container CMD:

    python /opt/instana/custom-collector/extensions/collect.py
"""

import logging
import time
from typing import TYPE_CHECKING

import pymysql

from extension_base.core import ExtensionBase

if TYPE_CHECKING:
    from extension_base.config.models import Endpoint
    from extension_base.metrics.emitter import MetricsEmitter

# When run as `python collect.py`, __name__ is "__main__" which is an
# anonymous logger.  Use an explicit name so log records are identifiable.
logger = logging.getLogger("mysql_collector")


def collect_mysql_metrics(endpoint: "Endpoint", emitter: "MetricsEmitter") -> None:
    """Query MySQL GLOBAL STATUS and emit metrics for the given endpoint."""
    host = endpoint.url
    creds = endpoint.credentials
    timeout = getattr(endpoint, "timeout", None) or 5

    start = time.monotonic()
    conn = None

    try:
        conn = pymysql.connect(
            host=host,
            port=getattr(endpoint, "port", None) or 3306,
            user=creds.username,
            password=creds.password,
            database="information_schema",
            connect_timeout=timeout,
            read_timeout=timeout,
            autocommit=True,
        )

        with conn.cursor() as cur:
            cur.execute("SHOW GLOBAL STATUS")
            status = {row[0]: row[1] for row in cur.fetchall()}

        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "Collected %d status rows from %s in %.1f ms",
            len(status), endpoint.id, duration_ms,
        )

        # ── counters (monotonic, cumulative) ────────────────────────────────
        emitter.report_metric(
            "counter",
            "mysql.connections.total",
            value=int(status.get("Connections", 0)),
            description="Total connection attempts since server start",
            unit="{connection}",
        )
        emitter.report_metric(
            "counter",
            "mysql.queries.total",
            value=int(status.get("Questions", 0)),
            description="Total queries executed since server start",
            unit="{query}",
        )
        emitter.report_metric(
            "counter",
            "mysql.slow_queries.total",
            value=int(status.get("Slow_queries", 0)),
            description="Queries exceeding long_query_time threshold",
            unit="{query}",
        )
        emitter.report_metric(
            "counter",
            "mysql.bytes.received",
            value=int(status.get("Bytes_received", 0)),
            description="Bytes received from all clients",
            unit="By",
        )
        emitter.report_metric(
            "counter",
            "mysql.bytes.sent",
            value=int(status.get("Bytes_sent", 0)),
            description="Bytes sent to all clients",
            unit="By",
        )

        # ── gauges (non-monotonic, current snapshot) ─────────────────────────
        emitter.report_metric(
            "gauge",
            "mysql.threads.connected",
            value=int(status.get("Threads_connected", 0)),
            description="Number of currently open connections",
            unit="{thread}",
        )
        emitter.report_metric(
            "gauge",
            "mysql.threads.running",
            value=int(status.get("Threads_running", 0)),
            description="Threads not sleeping (actively executing queries)",
            unit="{thread}",
        )
        emitter.report_metric(
            "gauge",
            "mysql.open_tables",
            value=int(status.get("Open_tables", 0)),
            description="Number of tables currently open",
            unit="{table}",
        )

        # ── histogram (collection round-trip latency) ───────────────────────
        emitter.report_metric(
            "histogram",
            "mysql.collection.duration",
            value=duration_ms,
            description="Time spent querying MySQL GLOBAL STATUS",
            unit="ms",
        )

    except pymysql.Error as exc:
        logger.exception("MySQL error on endpoint %s: %s", endpoint.id, exc)
        emitter.report_metric(
            "counter",
            "mysql.collection.errors",
            value=1,
            attributes={"error_type": type(exc).__name__},
            description="MySQL collection errors",
        )
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    extension = ExtensionBase()
    extension.run(collect_mysql_metrics)
