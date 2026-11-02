"""Benchmark synthetic telemetry generation and JSONL serialization."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
import time
from collections.abc import Callable

from telemetry_engine import iter_timeseries


class CountingTextWriter:
    """Text sink that counts serialized characters without doing disk I/O."""

    def __init__(self) -> None:
        self.characters = 0

    def write(self, text: str) -> int:
        self.characters += len(text)
        return len(text)


def benchmark_generation(count: int, seed: int) -> int:
    """Consume generated records and return the record count."""
    records = 0
    for _ in iter_timeseries(count, seed=seed):
        records += 1
    return records


def benchmark_jsonl(count: int, seed: int) -> int:
    """Generate and serialize records into a memory-free counting sink."""
    sink = CountingTextWriter()
    records = 0
    for record in iter_timeseries(count, seed=seed):
        sink.write(record.to_json())
        sink.write("\n")
        records += 1
    return records


def measure(
    count: int,
    repeats: int,
    seed: int,
    workload: Callable[[int, int], int],
) -> tuple[float, float]:
    """Return median seconds and records per second across repetitions."""
    durations = []
    for _ in range(repeats):
        start = time.perf_counter()
        processed = workload(count, seed)
        elapsed = time.perf_counter() - start
        if processed != count:
            raise RuntimeError(f"expected {count} records, processed {processed}")
        durations.append(elapsed)
    median_seconds = statistics.median(durations)
    throughput = count / median_seconds if median_seconds else 0.0
    return median_seconds, throughput


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=positive_int,
        default=[10_000, 100_000, 1_000_000],
        help="record counts to benchmark (default: 10000 100000 1000000)",
    )
    parser.add_argument("--repeats", type=positive_int, default=3)
    parser.add_argument("--seed", type=non_negative_int, default=42)
    parser.add_argument(
        "--workload",
        choices=("generation", "jsonl"),
        default="generation",
        help="measure record generation alone or generation plus JSONL serialization",
    )
    args = parser.parse_args()

    workload = benchmark_generation if args.workload == "generation" else benchmark_jsonl
    rows = []
    for count in args.sizes:
        median_seconds, throughput = measure(count, args.repeats, args.seed, workload)
        rows.append((args.workload, count, args.repeats, f"{median_seconds:.6f}",
                     f"{throughput:.2f}", args.seed))

    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(("workload", "records", "repeats", "median_seconds",
                     "records_per_second", "seed"))
    writer.writerows(rows)


if __name__ == "__main__":
    main()
