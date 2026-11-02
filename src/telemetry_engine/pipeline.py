"""Sequential validation, aggregation, and anomaly detection for telemetry."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
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


@dataclass(frozen=True, slots=True)
class RollingStatistics:
    """Rolling features for one input record; invalid records have no values."""

    record: TelemetryRecord
    is_valid: bool
    window_count: int
    moving_average: float | None
    moving_stddev: float | None
    is_anomaly: bool


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


@dataclass(slots=True)
class _RollingWindow:
    values: deque[float] = field(default_factory=deque)
    total: float = 0.0
    sum_of_squares: float = 0.0
    last_timestamp: float | None = None

    def statistics(self) -> tuple[float, float]:
        mean = self.total / len(self.values)
        variance = max(0.0, self.sum_of_squares / len(self.values) - mean * mean)
        return mean, math.sqrt(variance)

    def add(self, value: float, window_size: int) -> None:
        if len(self.values) == window_size:
            oldest = self.values.popleft()
            self.total -= oldest
            self.sum_of_squares -= oldest * oldest
        self.values.append(value)
        self.total += value
        self.sum_of_squares += value * value


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


def iter_rolling_statistics(
    records: Iterable[TelemetryRecord],
    *,
    window_size: int = 30,
    min_history: int = 5,
    sigma_threshold: float = 3.0,
) -> Iterator[RollingStatistics]:
    """Yield per-record rolling features grouped by host and metric.

    Moving averages and population standard deviations use the current sample
    and up to ``window_size - 1`` previous valid samples. Anomaly detection
    compares the current value with the prior window, excluding that value.
    It starts after ``min_history`` prior samples. Invalid records are yielded
    with empty features and do not change a series window. Timestamps must be
    non-decreasing within each host/metric series.
    """
    if window_size <= 0:
        raise ValueError("window_size must be positive")
    if min_history <= 0 or min_history > window_size:
        raise ValueError("min_history must be between 1 and window_size")
    if not math.isfinite(sigma_threshold) or sigma_threshold <= 0:
        raise ValueError("sigma_threshold must be finite and positive")

    windows: dict[tuple[str, str], _RollingWindow] = {}
    for record in records:
        if not _is_valid(record):
            yield RollingStatistics(record, False, 0, None, None, False)
            continue

        key = (record.host_id, record.metric)
        window = windows.get(key)
        if window is None:
            window = _RollingWindow()
            windows[key] = window
        if window.last_timestamp is not None and record.timestamp < window.last_timestamp:
            raise ValueError(f"timestamps decreased for host/metric series {key}")

        value = float(record.value)
        is_anomaly = False
        if len(window.values) >= min_history:
            previous_mean, previous_stddev = window.statistics()
            difference = abs(value - previous_mean)
            is_anomaly = (difference > sigma_threshold * previous_stddev
                          if previous_stddev > 0 else difference > 0)

        window.add(value, window_size)
        window.last_timestamp = record.timestamp
        moving_average, moving_stddev = window.statistics()
        yield RollingStatistics(
            record=record,
            is_valid=True,
            window_count=len(window.values),
            moving_average=moving_average,
            moving_stddev=moving_stddev,
            is_anomaly=is_anomaly,
        )
