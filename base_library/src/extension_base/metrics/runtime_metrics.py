# (c) Copyright IBM Corp. 2026
"""
Python runtime metrics for the Extension Base Library.

Registers observable callbacks on an OTel Meter that report live
process-level metrics pulled from ``psutil`` and the built-in ``gc``
and ``threading`` modules.

Metrics are pulled by the SDK on every export cycle (no separate
polling loop), so the collection interval is controlled entirely by the
``PeriodicExportingMetricReader`` — no extra threads or timers are
created here.

Registered metrics
------------------
Memory (psutil):
  ``instana.runtime.python.memory.rss``           – ObservableGauge, By
  ``instana.runtime.python.memory.vms``           – ObservableGauge, By
  ``instana.runtime.python.memory.percent``       – ObservableGauge, %

CPU (psutil):
  ``instana.runtime.python.cpu.utilization``      – ObservableGauge, %
  ``instana.runtime.python.cpu.time``             – ObservableCounter, s

Threads (threading):
  ``instana.runtime.python.thread.count``         – ObservableGauge, {thread}

GC (gc module):
  ``instana.runtime.python.gc.collections``       – ObservableCounter, {collection}
  ``instana.runtime.python.gc.objects.collected`` – ObservableCounter, {object}
"""

import gc
import logging
import os
import threading
from typing import TYPE_CHECKING, Iterable

import psutil

if TYPE_CHECKING:
    from opentelemetry.metrics import Meter

__all__ = ["register_python_runtime_metrics"]

logger = logging.getLogger(__name__)

_RUNTIME_ATTRS = {"metric.type": "runtime"}


def register_python_runtime_metrics(meter: "Meter") -> None:
    """Register all Python runtime observable metrics on *meter*."""
    from opentelemetry.metrics import CallbackOptions, Observation

    # Reuse a single Process instance so stateful methods like cpu_percent work
    try:
        proc = psutil.Process(os.getpid())
        # Prime psutil cpu_percent so the first real export is non-zero
        proc.cpu_percent(interval=None)
    except Exception:
        proc = None
        logger.debug("runtime_metrics: failed to initialize psutil.Process", exc_info=True)

    # ------------------------------------------------------------------
    # Memory — RSS
    # ------------------------------------------------------------------

    def _observe_rss(_opts: CallbackOptions) -> Iterable[Observation]:
        if proc is None:
            return
        try:
            yield Observation(
                proc.memory_info().rss,
                attributes=_RUNTIME_ATTRS,
            )
        except Exception:
            logger.debug("runtime_metrics: rss read failed", exc_info=True)

    meter.create_observable_gauge(
        "instana.runtime.python.memory.rss",
        callbacks=[_observe_rss],
        description="Resident Set Size of the Python process",
        unit="By",
    )

    # ------------------------------------------------------------------
    # Memory — VMS
    # ------------------------------------------------------------------

    def _observe_vms(_opts: CallbackOptions) -> Iterable[Observation]:
        if proc is None:
            return
        try:
            yield Observation(
                proc.memory_info().vms,
                attributes=_RUNTIME_ATTRS,
            )
        except Exception:
            logger.debug("runtime_metrics: vms read failed", exc_info=True)

    meter.create_observable_gauge(
        "instana.runtime.python.memory.vms",
        callbacks=[_observe_vms],
        description="Virtual Memory Size of the Python process",
        unit="By",
    )

    # ------------------------------------------------------------------
    # Memory — percent
    # ------------------------------------------------------------------

    def _observe_mem_percent(_opts: CallbackOptions) -> Iterable[Observation]:
        if proc is None:
            return
        try:
            yield Observation(
                proc.memory_percent(),
                attributes=_RUNTIME_ATTRS,
            )
        except Exception:
            logger.debug(
                "runtime_metrics: memory percent read failed", exc_info=True
            )

    meter.create_observable_gauge(
        "instana.runtime.python.memory.percent",
        callbacks=[_observe_mem_percent],
        description="Memory usage percentage of the Python process",
        unit="%",
    )

    # ------------------------------------------------------------------
    # CPU — utilization
    # ------------------------------------------------------------------

    def _observe_cpu_util(_opts: CallbackOptions) -> Iterable[Observation]:
        if proc is None:
            return
        try:
            yield Observation(
                proc.cpu_percent(interval=None),
                attributes=_RUNTIME_ATTRS,
            )
        except Exception:
            logger.debug(
                "runtime_metrics: cpu utilization read failed", exc_info=True
            )

    meter.create_observable_gauge(
        "instana.runtime.python.cpu.utilization",
        callbacks=[_observe_cpu_util],
        description="CPU utilization percentage of the Python process",
        unit="%",
    )

    # ------------------------------------------------------------------
    # CPU — time (user + system, cumulative)
    # ------------------------------------------------------------------

    def _observe_cpu_time(_opts: CallbackOptions) -> Iterable[Observation]:
        if proc is None:
            return
        try:
            ct = proc.cpu_times()
            yield Observation(
                ct.user + ct.system,
                attributes=_RUNTIME_ATTRS,
            )
        except Exception:
            logger.debug(
                "runtime_metrics: cpu time read failed", exc_info=True
            )

    # Using ObservableCounter here because cumulative time is monotonic
    meter.create_observable_counter(
        "instana.runtime.python.cpu.time",
        callbacks=[_observe_cpu_time],
        description="Cumulative CPU time (user + system) in seconds",
        unit="s",
    )

    # ------------------------------------------------------------------
    # Threads
    # ------------------------------------------------------------------

    def _observe_thread_count(_opts: CallbackOptions) -> Iterable[Observation]:
        yield Observation(threading.active_count(), attributes=_RUNTIME_ATTRS)

    meter.create_observable_gauge(
        "instana.runtime.python.thread.count",
        callbacks=[_observe_thread_count],
        description="Total number of active Python threads",
        unit="{thread}",
    )

    # ------------------------------------------------------------------
    # GC — collections per generation (cumulative counter)
    # ------------------------------------------------------------------

    def _collect_gc_collections(
        _opts: CallbackOptions,
    ) -> Iterable[Observation]:
        for generation, stats in enumerate(gc.get_stats()):
            yield Observation(
                stats["collections"],
                attributes={**_RUNTIME_ATTRS, "generation": str(generation)},
            )

    meter.create_observable_counter(
        "instana.runtime.python.gc.collections",
        callbacks=[_collect_gc_collections],
        description="Number of GC collections by generation",
        unit="{collection}",
    )

    # ------------------------------------------------------------------
    # GC — objects collected per generation (cumulative counter)
    # ------------------------------------------------------------------

    def _collect_gc_objects_collected(
        _opts: CallbackOptions,
    ) -> Iterable[Observation]:
        for generation, stats in enumerate(gc.get_stats()):
            yield Observation(
                stats["collected"],
                attributes={**_RUNTIME_ATTRS, "generation": str(generation)},
            )

    meter.create_observable_counter(
        "instana.runtime.python.gc.objects.collected",
        callbacks=[_collect_gc_objects_collected],
        description="Number of objects collected by GC per generation",
        unit="{object}",
    )
