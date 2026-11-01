"""Tools for generating and processing synthetic system telemetry."""

from .generate import TelemetryRecord, iter_records
from .pipeline import MetricSummary, ProcessingSummary, process_records

__all__ = [
    "MetricSummary",
    "ProcessingSummary",
    "TelemetryRecord",
    "iter_records",
    "process_records",
]
