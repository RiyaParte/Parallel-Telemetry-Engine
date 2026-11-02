# Parallel Telemetry Engine

A High-Performance Computing (HPC) project exploring parallel data processing, workload distribution, and performance optimization through large-scale telemetry workloads.

## Overview

The Parallel Telemetry Engine is a Python-based project designed to process large volumes of synthetic system telemetry data and investigate how parallel computing techniques can improve processing performance.

The project starts with a sequential processing pipeline and progressively introduces multiprocessing and distributed execution using MPI. Performance is evaluated across different dataset sizes and worker counts to understand speedup, scalability, and computational bottlenecks.

## Objectives

- Build a telemetry processing pipeline with validation, transformation, aggregation, and anomaly detection.
- Generate synthetic telemetry datasets at configurable scales.
- Establish a sequential performance baseline.
- Implement parallel processing using Python multiprocessing.
- Explore distributed processing with MPI.
- Benchmark execution time, throughput, speedup, and parallel efficiency.
- Investigate performance bottlenecks, including I/O, memory usage, and workload imbalance.

## Planned Tech Stack

- **Language:** Python
- **Data Processing:** Pandas, PyArrow
- **Storage:** Apache Parquet
- **Parallel Computing:** Python multiprocessing, mpi4py
- **Benchmarking:** Python, Matplotlib
- **Testing:** pytest

## Development Roadmap

- [x] Build a synthetic telemetry data generator and measure its throughput across dataset sizes.
- [x] Implement sequential validation, aggregation, and rolling-window statistics.
- [x] Establish the sequential processing baseline across dataset sizes.
- [ ] Implement multiprocessing-based parallel processing.
- [ ] Compare static and dynamic workload distribution.
- [ ] Introduce MPI for distributed execution.
- [ ] Measure speedup, parallel efficiency, and scalability.
- [ ] Profile and optimize I/O, memory usage, and processing performance.
- [ ] Build a simple, telemetry-aware local tool as a reusable Python library and CLI. It should detect supported telemetry formats, apply built-in processing profiles, and choose worker counts automatically.

## Performance Evaluation

The engine will be evaluated using:

- Execution time
- Processing throughput
- CPU and memory utilization
- Parallel speedup
- Parallel efficiency
- Strong and weak scaling

Benchmark results will be documented as implementations and experiments are completed.

## Project Status

**In development.** The project has a deterministic, regular time-series generator, a sequential validation and aggregation pipeline with rolling statistics, and initial generation and processing baselines. Multiprocessing comparison is next.

## Getting Started

The project currently uses only the Python standard library. From the repository root, install it in editable mode:

```bash
python3 -m pip install -e .
```

Generate regular time-series samples from Python and optionally write them as JSON Lines:

```python
from telemetry_engine import iter_timeseries
from telemetry_engine.generate import write_jsonl

with open("telemetry.jsonl", "w", encoding="utf-8") as output:
    count = write_jsonl(iter_timeseries(100_000, seed=42), output)
print(f"Wrote {count} records")
```

`iter_timeseries` yields one record at a time, so creating a large workload does not require keeping the whole dataset in memory. It emits samples in regular timestamp rounds across 10 hosts and four metrics; each host/metric series is sampled once per second by default. Values follow smooth, metric-specific patterns with noise and deterministic spikes in about 1% of samples. Use `invalid_rate=0` for all-valid data or `invalid_rate=1` for all-invalid data. The default is 1% invalid records. A fixed seed produces the same records on repeated runs. `iter_records` remains available for simple independent-record examples and tests; benchmarks use `iter_timeseries`.

## Sequential Pipeline

`process_records(records)` consumes an iterable once. It counts and skips invalid records, then reports count, minimum, maximum, and average for each metric. It also counts threshold anomalies among valid records: CPU and memory above 90%, temperature above 80 C, and disk read speed above 450 MB/s. These simple thresholds are project defaults for learning and can be adjusted in `src/telemetry_engine/pipeline.py`.

`iter_rolling_statistics(records, window_size=30)` yields rolling features for each record, keeping an independent window for every host/metric pair. It reports a moving average and population standard deviation; it flags a value when it is more than three prior-window standard deviations from the prior mean, after at least five prior samples. Invalid rows have no rolling values and do not update the window. Input timestamps must be non-decreasing within each series.

## Benchmarks

Run the generation baseline after installing the package:

```bash
python3 benchmarks/benchmark_generation.py --sizes 10000 100000 1000000 --repeats 3 --seed 42 > benchmarks/results/generation_baseline.csv
```

The CSV output reports median elapsed time and records per second for each dataset size. To include JSONL serialization cost without measuring filesystem speed, use `--workload jsonl`. Set `--seed` to keep the generated workload reproducible. The benchmark uses regular time series and consumes records without saving a data file.

### Initial generation baseline

Measured with Python 3.13.0 on macOS 14.6.1 (Apple Silicon), using seed 42, three measured trials, and the median time. This measures generation only; it does not include processing or disk I/O.

| Records | Median time | Throughput |
| ---: | ---: | ---: |
| 10,000 | 0.015689 s | 637,374 records/s |
| 100,000 | 0.155620 s | 642,592 records/s |
| 1,000,000 | 1.546604 s | 646,578 records/s |

These results use regular series across 10 hosts and four metrics at 1-second intervals, with seed 42 and three trials. The raw generator timings are in [generation_baseline.csv](benchmarks/results/generation_baseline.csv). They are a local reference point, not a comparison against another implementation. Re-run the command on the same machine when measuring changes.

### Sequential processing baseline

Run the sequential pipeline against the same seeded record sizes. The benchmark creates each dataset before starting the timer, so these timings cover validation, aggregation, and anomaly detection, but exclude data generation and file I/O:

```bash
python3 benchmarks/benchmark_sequential.py --sizes 10000 100000 1000000 --repeats 3 --seed 42 --output benchmarks/results/sequential_baseline.csv
python3 benchmarks/benchmark_rolling.py --sizes 10000 100000 1000000 --repeats 3 --seed 42 --window-size 30 --min-history 5 --sigma-threshold 3 --output benchmarks/results/rolling_baseline.csv
python3 benchmarks/plot_results.py benchmarks/results/sequential_baseline.csv benchmarks/results/rolling_baseline.csv --output benchmarks/results/sequential_processing_time.svg
```

The raw CSV includes valid, invalid, and anomalous record counts, timing, throughput, and environment details. This local run used Python 3.13.0 on macOS 14.6.1 (Apple Silicon), with seed 42 and three measured trials:

| Records | Valid | Invalid | Anomalies | Median time | Throughput |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 10,000 | 9,908 | 92 | 73 | 0.005247 s | 1,906,017 records/s |
| 100,000 | 99,028 | 972 | 733 | 0.052065 s | 1,920,688 records/s |
| 1,000,000 | 990,174 | 9,826 | 8,217 | 0.536920 s | 1,862,476 records/s |

### Rolling statistics baseline

The rolling benchmark measures a 30-sample moving average and population standard deviation per host/metric series. A sample is compared with the prior window for anomalies after five history samples; the current sample is excluded from that comparison. Data generation remains outside the timed section.

| Records | Anomalies | Median time | Throughput |
| ---: | ---: | ---: | ---: |
| 10,000 | 182 | 0.016634 s | 601,172 records/s |
| 100,000 | 1,953 | 0.165236 s | 605,194 records/s |
| 1,000,000 | 19,055 | 1.635817 s | 611,315 records/s |

The raw measurements and window parameters are in [rolling_baseline.csv](benchmarks/results/rolling_baseline.csv). The chart compares the original sequential summary with the rolling workload:

![Sequential processing time and rolling-statistics comparison](benchmarks/results/sequential_processing_time.svg)

To compare a future implementation, pass its result CSV alongside this one to `plot_results.py`. The chart groups rows by the `mode` column, so use a distinct mode such as `multiprocessing` in future benchmark results. It plots median elapsed time against record count on a logarithmic x-axis. These measurements are hardware- and runtime-specific reference points.

Install the development extra to run the unit tests with pytest:

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
```

## Learning Goals

This project aims to develop practical knowledge of HPC fundamentals, parallel programming, distributed execution, performance profiling, and scalability analysis.
