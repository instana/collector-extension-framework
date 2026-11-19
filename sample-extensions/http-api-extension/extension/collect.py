#!/usr/bin/env python3
# (c) Copyright IBM Corp. 2026
"""
HTTP API Collector Extension.

Polls a JSON REST endpoint and emits OTel metrics via the Extension Base Library.
Run as the container CMD:

    python /opt/instana/custom-collector/extensions/collect.py
"""

import logging
import time
from typing import TYPE_CHECKING

import requests

from extension_base.config.credentials import CredentialsManager
from extension_base.core import ExtensionBase

if TYPE_CHECKING:
    from extension_base.config.models import Endpoint
    from extension_base.metrics.emitter import MetricsEmitter

logger = logging.getLogger("http_api_collector")


METRIC_DEFINITIONS = (
    (
        "gauge",
        "demo.api.uptime",
        "uptime_seconds",
        "Demo API uptime in seconds",
        "s",
    ),
    (
        "gauge",
        "demo.api.active_requests",
        "active_requests",
        "Current number of active requests",
        "{request}",
    ),
    (
        "counter",
        "demo.api.error_count",
        "error_count",
        "Total number of errors reported by the demo API",
        "{error}",
    ),
    (
        "gauge",
        "demo.api.queue_depth",
        "queue_depth",
        "Current queue depth reported by the demo API",
        "{item}",
    ),
)


def build_stats_url(endpoint: "Endpoint") -> str:
    port = f":{endpoint.port}" if getattr(endpoint, "port", None) else ""
    return f"http://{endpoint.url}{port}/stats"


def collect_http_api_metrics(endpoint: "Endpoint", emitter: "MetricsEmitter") -> None:
    """Fetch JSON stats from the configured endpoint and emit metrics."""
    timeout = getattr(endpoint, "timeout", None) or 5
    headers = {"Accept": "application/json"}

    if endpoint.credentials is not None:
        headers.update(CredentialsManager().get_auth_header(endpoint.credentials))

    start = time.monotonic()

    try:
        response = requests.get(
            build_stats_url(endpoint),
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()

        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "Collected stats from %s in %.1f ms: %s",
            endpoint.id,
            duration_ms,
            payload,
        )

        for metric_type, metric_name, field, description, unit in METRIC_DEFINITIONS:
            emitter.report_metric(
                metric_type,
                metric_name,
                value=float(payload.get(field, 0)),
                description=description,
                unit=unit,
            )

        jobs = payload.get("jobs", [])
        jobs_total = len(jobs)
        failed_jobs = sum(1 for job in jobs if job.get("status") == "failed")
        failure_rate = (failed_jobs / jobs_total) if jobs_total else 0

        emitter.report_metric(
            "gauge",
            "demo.api.jobs.total",
            value=jobs_total,
            description="Number of jobs returned by the demo API",
            unit="{job}",
        )
        emitter.report_metric(
            "gauge",
            "demo.api.jobs.failed",
            value=failed_jobs,
            description="Number of failed jobs returned by the demo API",
            unit="{job}",
        )
        emitter.report_metric(
            "gauge",
            "demo.api.jobs.failure_rate",
            value=failure_rate,
            description="Fraction of jobs in failed state",
            unit="1",
        )
        emitter.report_metric(
            "histogram",
            "demo.api.collection.duration",
            value=duration_ms,
            description="Time spent fetching the demo API stats endpoint",
            unit="ms",
        )

    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 0
        logger.exception("HTTP error on endpoint %s: %s", endpoint.id, exc)
        emitter.report_metric(
            "counter",
            "demo.api.collection.errors",
            value=1,
            attributes={"error_type": "http", "status_code": str(status_code)},
            description="HTTP API collection errors",
        )
        raise
    except requests.RequestException as exc:
        logger.exception("Request error on endpoint %s: %s", endpoint.id, exc)
        emitter.report_metric(
            "counter",
            "demo.api.collection.errors",
            value=1,
            attributes={"error_type": "network"},
            description="HTTP API collection errors",
        )
        raise


if __name__ == "__main__":
    extension = ExtensionBase()
    extension.run(collect_http_api_metrics)
