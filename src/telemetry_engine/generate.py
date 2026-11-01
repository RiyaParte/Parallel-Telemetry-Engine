"""Generate deterministic synthetic telemetry records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
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
