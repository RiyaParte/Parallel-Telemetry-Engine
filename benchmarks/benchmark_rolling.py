"""Benchmark sequential rolling statistics on seeded time-series data."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import platform
import statistics
import sys
from time import perf_counter

from telemetry_engine import TelemetryRecord, iter_rolling_statistics, iter_timeseries


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def positive_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return number


def summarize_rolling_run(
    records: list[TelemetryRecord],
    *,
    window_size: int,
    min_history: int,
    sigma_threshold: float,
) -> tuple[int, int, int, int]:
    records_seen = valid_records = invalid_records = anomalies = 0
    for result in iter_rolling_statistics(
        records,
        window_size=window_size,
        min_history=min_history,
        sigma_threshold=sigma_threshold,
    ):
        records_seen += 1
        valid_records += int(result.is_valid)
        invalid_records += int(not result.is_valid)
        anomalies += int(result.is_anomaly)
    return records_seen, valid_records, invalid_records, anomalies


def measure(records: list[TelemetryRecord], args: argparse.Namespace) -> tuple[float, tuple[int, int, int, int]]:
    elapsed_times = []
    expected_counts = None
    for _ in range(args.repeats):
        started = perf_counter()
        counts = summarize_rolling_run(
            records,
            window_size=args.window_size,
            min_history=args.min_history,
            sigma_threshold=args.sigma_threshold,
        )
        elapsed_times.append(perf_counter() - started)
        if expected_counts is None:
            expected_counts = counts
        elif counts != expected_counts:
            raise RuntimeError("rolling results changed between benchmark trials")
    if expected_counts is None:
        raise RuntimeError("no benchmark trials were run")
    return statistics.median(elapsed_times), expected_counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=positive_int,
                        default=[10_000, 100_000, 1_000_000])
    parser.add_argument("--repeats", type=positive_int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--window-size", type=positive_int, default=30)
    parser.add_argument("--min-history", type=positive_int, default=5)
    parser.add_argument("--sigma-threshold", type=positive_float, default=3.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.min_history > args.window_size:
        parser.error("--min-history must not exceed --window-size")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow((
            "mode", "records", "valid_records", "invalid_records", "anomaly_records",
            "repeats", "median_seconds", "records_per_second", "seed",
            "python_version", "platform", "window_size", "min_history", "sigma_threshold",
        ))
        for size in args.sizes:
            # Keep data generation outside the timed rolling-processing section.
            records = list(iter_timeseries(size, seed=args.seed))
            median_seconds, counts = measure(records, args)
            records_seen, valid_records, invalid_records, anomalies = counts
            if records_seen != size:
                raise RuntimeError(f"expected {size} records, processed {records_seen}")
            throughput = size / median_seconds if median_seconds else 0.0
            writer.writerow((
                "sequential_rolling", size, valid_records, invalid_records, anomalies,
                args.repeats, f"{median_seconds:.6f}", f"{throughput:.2f}", args.seed,
                platform.python_version(), platform.platform(), args.window_size,
                args.min_history, args.sigma_threshold,
            ))


if __name__ == "__main__":
    main()
