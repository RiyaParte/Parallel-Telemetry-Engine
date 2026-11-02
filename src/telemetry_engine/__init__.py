"""Tools for generating and processing synthetic system telemetry."""

from .generate import TelemetryRecord, iter_records, iter_timeseries
from .pipeline import MetricSummary, ProcessingSummary, process_records

__all__ = [
    "MetricSummary",
    "ProcessingSummary",
    "TelemetryRecord",
    "iter_records",
    "iter_timeseries",
    "process_records",
]
