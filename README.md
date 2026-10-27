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

- [x] Build a synthetic telemetry data generator.
- [ ] Implement the sequential processing pipeline.
- [ ] Establish performance baselines across dataset sizes.
- [ ] Implement multiprocessing-based parallel processing.
- [ ] Compare static and dynamic workload distribution.
- [ ] Introduce MPI for distributed execution.
- [ ] Measure speedup, parallel efficiency, and scalability.
- [ ] Profile and optimize I/O, memory usage, and processing performance.

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

**In development.** The first milestone provides a deterministic, streaming synthetic telemetry generator. The sequential processing baseline is next.

## Getting Started

The project currently uses only the Python standard library. From the repository root, install it in editable mode:

```bash
python -m pip install -e .
```

Generate records from Python and optionally write them as JSON Lines:

```python
from telemetry_engine import iter_records
from telemetry_engine.generate import write_jsonl

with open("telemetry.jsonl", "w", encoding="utf-8") as output:
    count = write_jsonl(iter_records(100_000, seed=42), output)
print(f"Wrote {count} records")
```

`iter_records` yields one record at a time, so creating a large workload does not require keeping the whole dataset in memory. Use `invalid_rate=0` for all-valid data or `invalid_rate=1` for all-invalid data. The default is 1% invalid records. A fixed seed produces the same records on repeated runs.

## Generation Benchmark

Run the sequential generation baseline after installing the package:

```bash
python benchmarks/benchmark_generation.py --sizes 10000 100000 1000000 --repeats 3
```

The CSV output reports median elapsed time and records per second for each dataset size. To include JSONL serialization cost without measuring filesystem speed, use `--workload jsonl`. Set `--seed` to keep the generated workload reproducible. These numbers establish a generator baseline; processing and parallel speedup benchmarks will follow once those pipeline stages are implemented.

Install the development extra to run the unit tests with pytest:

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## Learning Goals

This project aims to develop practical knowledge of HPC fundamentals, parallel programming, distributed execution, performance profiling, and scalability analysis.
