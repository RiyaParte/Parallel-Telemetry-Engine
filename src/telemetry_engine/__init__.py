"""Tools for generating and processing synthetic system telemetry."""

from .generate import TelemetryRecord, iter_records, iter_timeseries
from .pipeline import (
    MetricSummary,
    ProcessingSummary,
    RollingStatistics,
    iter_rolling_statistics,
    process_records,
)

__all__ = [
    "MetricSummary",
    "ProcessingSummary",
    "RollingStatistics",
    "TelemetryRecord",
    "iter_records",
    "iter_timeseries",
    "iter_rolling_statistics",
    "process_records",
]
