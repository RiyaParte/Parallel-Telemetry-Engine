"""Benchmark sequential processing on reproducible, in-memory datasets."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import platform
import statistics
import sys
from time import perf_counter

from telemetry_engine import ProcessingSummary, TelemetryRecord, iter_timeseries, process_records


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def measure(records: list[TelemetryRecord], repeats: int) -> tuple[float, ProcessingSummary]:
    """Return median processing time and the deterministic processing summary."""
    durations = []
    expected_summary = None
    for _ in range(repeats):
        started = perf_counter()
        summary = process_records(records)
        durations.append(perf_counter() - started)
        if expected_summary is None:
            expected_summary = summary
        elif summary != expected_summary:
            raise RuntimeError("processing results changed between benchmark trials")

    return statistics.median(durations), expected_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes", nargs="+", type=positive_int,
        default=[10_000, 100_000, 1_000_000],
        help="record counts to benchmark (default: 10000 100000 1000000)",
    )
    parser.add_argument("--repeats", type=positive_int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output", type=Path,
        help="CSV output path (default: write CSV to stdout)",
    )
    args = parser.parse_args()

    columns = (
        "mode", "records", "valid_records", "invalid_records", "anomaly_records",
        "repeats", "median_seconds", "records_per_second", "seed",
        "python_version", "platform",
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        output = args.output.open("w", newline="", encoding="utf-8")
    else:
        output = sys.stdout
    try:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(columns)
        for size in args.sizes:
            # Generate once before timing, so this benchmark measures processing only.
            records = list(iter_timeseries(size, seed=args.seed))
            median_seconds, summary = measure(records, args.repeats)
            throughput = size / median_seconds if median_seconds else 0.0
            writer.writerow((
                "sequential", size, summary.valid_records, summary.invalid_records,
                summary.anomaly_records, args.repeats, f"{median_seconds:.6f}",
                f"{throughput:.2f}", args.seed, platform.python_version(),
                platform.platform(),
            ))
    finally:
        if args.output:
            output.close()


if __name__ == "__main__":
    main()
