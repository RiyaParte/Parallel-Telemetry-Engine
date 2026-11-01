"""Sequential validation, aggregation, and anomaly detection for telemetry."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import math

from .generate import TelemetryRecord


# Each metric maps to its expected unit, valid value range, and anomaly limit.
_METRIC_RULES = {
    "cpu_percent": ("%", 0.0, 100.0, 90.0),
    "memory_percent": ("%", 0.0, 100.0, 90.0),
    "temperature_c": ("C", -40.0, 150.0, 80.0),
    "disk_read_mbps": ("MB/s", 0.0, 10_000.0, 450.0),
}


@dataclass(frozen=True, slots=True)
class MetricSummary:
    """Aggregate values for one valid metric type."""

    count: int
    minimum: float
    maximum: float
    average: float
    anomalies: int


@dataclass(frozen=True, slots=True)
class ProcessingSummary:
    """Counts and metric aggregates produced by a pipeline run."""

    records_seen: int
    valid_records: int
    invalid_records: int
    anomaly_records: int
    metrics: dict[str, MetricSummary]


@dataclass(slots=True)
class _MetricAccumulator:
    count: int = 0
    total: float = 0.0
    minimum: float = math.inf
    maximum: float = -math.inf
    anomalies: int = 0

    def add(self, value: float, is_anomaly: bool) -> None:
        self.count += 1
        self.total += value
        self.minimum = min(self.minimum, value)
        self.maximum = max(self.maximum, value)
        self.anomalies += int(is_anomaly)

    def to_summary(self) -> MetricSummary:
        return MetricSummary(
            count=self.count,
            minimum=self.minimum,
            maximum=self.maximum,
            average=self.total / self.count,
            anomalies=self.anomalies,
        )


def _is_valid(record: TelemetryRecord) -> bool:
    """Return whether a record has a known metric and valid finite values."""
    if not isinstance(record, TelemetryRecord):
        return False
    if not isinstance(record.host_id, str) or not record.host_id.strip():
        return False
    if (not isinstance(record.timestamp, (int, float))
            or isinstance(record.timestamp, bool)
            or not math.isfinite(record.timestamp)):
        return False
    if not isinstance(record.metric, str) or record.metric not in _METRIC_RULES:
        return False
    if not isinstance(record.unit, str):
        return False
    if (not isinstance(record.value, (int, float))
            or isinstance(record.value, bool)
            or not math.isfinite(record.value)):
        return False

    unit, minimum, maximum, _ = _METRIC_RULES[record.metric]
    return (
        record.unit == unit
        and minimum <= record.value <= maximum
    )


def process_records(records: Iterable[TelemetryRecord]) -> ProcessingSummary:
    """Validate records, aggregate valid values, and count threshold anomalies.

    Invalid records are counted and skipped. Anomaly thresholds are strict
    greater-than comparisons, so a value exactly at its limit is not an
    anomaly. The iterable is consumed once and is never copied into memory.
    """
    records_seen = 0
    invalid_records = 0
    anomaly_records = 0
    accumulators: dict[str, _MetricAccumulator] = {}

    for record in records:
        records_seen += 1
        if not _is_valid(record):
            invalid_records += 1
            continue

        # _is_valid guarantees a known metric and a finite numeric value.
        rules = _METRIC_RULES[record.metric]
        value = record.value
        is_anomaly = value > rules[3]
        accumulator = accumulators.get(record.metric)
        if accumulator is None:
            accumulator = _MetricAccumulator()
            accumulators[record.metric] = accumulator
        accumulator.add(value, is_anomaly)
        anomaly_records += int(is_anomaly)

    metrics = {name: accumulator.to_summary()
               for name, accumulator in sorted(accumulators.items())}
    valid_records = records_seen - invalid_records
    return ProcessingSummary(
        records_seen=records_seen,
        valid_records=valid_records,
        invalid_records=invalid_records,
        anomaly_records=anomaly_records,
        metrics=metrics,
    )
