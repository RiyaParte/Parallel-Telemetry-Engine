"""Generate deterministic synthetic telemetry records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import random
from typing import Iterator, TextIO


@dataclass(frozen=True, slots=True)
class TelemetryRecord:
    """One system measurement. ``value`` is None for deliberately invalid data."""

    timestamp: float
    host_id: str
    metric: str
    value: float | None
    unit: str

    def to_json(self) -> str:
        """Return this record as one compact JSON line."""
        return json.dumps(asdict(self), separators=(",", ":"), allow_nan=False)


_METRICS = (("cpu_percent", "%", 0.0, 100.0),
            ("memory_percent", "%", 0.0, 100.0),
            ("temperature_c", "C", 20.0, 95.0),
            ("disk_read_mbps", "MB/s", 0.0, 500.0))

_ANOMALY_OFFSETS = (55.0, 42.0, 30.0, 400.0)


def iter_timeseries(
    count: int,
    *,
    seed: int = 0,
    host_count: int = 10,
    invalid_rate: float = 0.01,
    start_timestamp: float = 1_700_000_000.0,
    sample_interval_seconds: float = 1.0,
) -> Iterator[TelemetryRecord]:
    """Yield regular, deterministic samples across host and metric series.

    ``count`` is the total number of measurement records. Records are emitted
    in timestamp rounds across each host and metric, so every host/metric pair
    gets a sample at each configured interval. Values follow a smooth baseline
    with small noise and occasional injected spikes. Invalid records have an
    empty host ID or missing value for validation tests.
    """
    if count < 0:
        raise ValueError("count must be non-negative")
    if host_count <= 0:
        raise ValueError("host_count must be positive")
    if not 0.0 <= invalid_rate <= 1.0:
        raise ValueError("invalid_rate must be between 0 and 1")
    if not math.isfinite(start_timestamp):
        raise ValueError("start_timestamp must be finite")
    if not math.isfinite(sample_interval_seconds) or sample_interval_seconds <= 0:
        raise ValueError("sample_interval_seconds must be finite and positive")

    series_count = host_count * len(_METRICS)
    rng = random.Random(seed)
    for record_index in range(count):
        series_index = record_index % series_count
        host_index, metric_index = divmod(series_index, len(_METRICS))
        sample_index = record_index // series_count
        metric, unit, minimum, maximum = _METRICS[metric_index]
        phase = host_index * 0.37 + metric_index * 0.91
        noise = rng.gauss(0.0, (2.0, 0.8, 0.7, 15.0)[metric_index])

        if metric_index == 0:  # CPU usage varies over short workload cycles.
            value = 35.0 + 9.0 * math.sin(sample_index / 18.0 + phase) + noise
        elif metric_index == 1:  # Memory usage grows slowly over time.
            value = 48.0 + sample_index * 0.0003 + 2.5 * math.sin(sample_index / 240.0 + phase) + noise
        elif metric_index == 2:
            value = 55.0 + 4.0 * math.sin(sample_index / 120.0 + phase) + noise
        else:  # Disk reads vary with periodic I/O bursts.
            value = 120.0 + 55.0 * math.sin(sample_index / 17.0 + phase) + noise

        is_spike = sample_index > 0 and (sample_index + host_index * 13 + metric_index * 29) % 101 == 0
        if is_spike:
            value += _ANOMALY_OFFSETS[metric_index]
        value = round(min(maximum, max(minimum, value)), 3)

        is_invalid = rng.random() < invalid_rate
        invalid_host = is_invalid and rng.random() < 0.5
        host_id = "" if invalid_host else f"host-{host_index + 1:03d}"
        if is_invalid and not invalid_host:
            value = None

        yield TelemetryRecord(
            timestamp=start_timestamp + sample_index * sample_interval_seconds,
            host_id=host_id,
            metric=metric,
            value=value,
            unit=unit,
        )


def iter_records(
    count: int,
    *,
    seed: int = 0,
    invalid_rate: float = 0.01,
    start_timestamp: float = 1_700_000_000.0,
) -> Iterator[TelemetryRecord]:
    """Yield ``count`` records from a reproducible synthetic workload.

    Invalid records use a missing host ID or missing value so that the next
    milestone's validation stage has real cases to handle. ``invalid_rate``
    must be between 0 and 1 inclusive. The iterator keeps memory usage bounded.
    """
    if count < 0:
        raise ValueError("count must be non-negative")
    if not 0.0 <= invalid_rate <= 1.0:
        raise ValueError("invalid_rate must be between 0 and 1")

    rng = random.Random(seed)
    for index in range(count):
        metric, unit, minimum, maximum = rng.choice(_METRICS)
        is_invalid = rng.random() < invalid_rate
        invalid_host = is_invalid and rng.random() < 0.5
        host_id = "" if invalid_host else f"host-{rng.randrange(1, 101):03d}"
        value = None if is_invalid and not invalid_host else round(rng.uniform(minimum, maximum), 3)
        yield TelemetryRecord(
            timestamp=start_timestamp + index,
            host_id=host_id,
            metric=metric,
            value=value,
            unit=unit,
        )


def write_jsonl(records: Iterator[TelemetryRecord], destination: TextIO) -> int:
    """Write records as JSON Lines and return the number written."""
    written = 0
    for record in records:
        destination.write(record.to_json())
        destination.write("\n")
        written += 1
    return written
