import math
import unittest

from telemetry_engine import (
    TelemetryRecord,
    iter_rolling_statistics,
    iter_timeseries,
    process_records,
)


class ProcessRecordsTests(unittest.TestCase):
    def test_empty_input_returns_zero_counts(self):
        summary = process_records([])
        self.assertEqual(summary.records_seen, 0)
        self.assertEqual(summary.valid_records, 0)
        self.assertEqual(summary.invalid_records, 0)
        self.assertEqual(summary.anomaly_records, 0)
        self.assertEqual(summary.metrics, {})

    def test_aggregates_valid_records_and_counts_anomalies(self):
        records = [
            TelemetryRecord(1.0, "host-001", "cpu_percent", 45.0, "%"),
            TelemetryRecord(2.0, "host-002", "cpu_percent", 95.0, "%"),
            TelemetryRecord(3.0, "host-001", "temperature_c", 80.0, "C"),
        ]

        summary = process_records(records)

        self.assertEqual((summary.records_seen, summary.valid_records), (3, 3))
        self.assertEqual(summary.anomaly_records, 1)
        self.assertEqual(summary.metrics["cpu_percent"].count, 2)
        self.assertEqual(summary.metrics["cpu_percent"].minimum, 45.0)
        self.assertEqual(summary.metrics["cpu_percent"].maximum, 95.0)
        self.assertEqual(summary.metrics["cpu_percent"].average, 70.0)
        self.assertEqual(summary.metrics["cpu_percent"].anomalies, 1)
        self.assertEqual(summary.metrics["temperature_c"].anomalies, 0)

    def test_skips_invalid_records(self):
        records = [
            TelemetryRecord(1.0, "", "cpu_percent", 40.0, "%"),
            TelemetryRecord(2.0, "host-001", "cpu_percent", None, "%"),
            TelemetryRecord(3.0, "host-001", "unknown", 40.0, "%"),
            TelemetryRecord(4.0, "host-001", "cpu_percent", math.nan, "%"),
            TelemetryRecord(5.0, "host-001", "cpu_percent", 101.0, "%"),
            TelemetryRecord(6.0, "host-001", "cpu_percent", 40.0, "C"),
        ]

        summary = process_records(records)

        self.assertEqual(summary.records_seen, 6)
        self.assertEqual(summary.invalid_records, 6)
        self.assertEqual(summary.valid_records, 0)
        self.assertEqual(summary.metrics, {})

    def test_rejects_malformed_field_types_and_non_finite_timestamps(self):
        records = [
            TelemetryRecord(float("nan"), "host-001", "cpu_percent", 50.0, "%"),
            TelemetryRecord(1.0, None, "cpu_percent", 50.0, "%"),
            TelemetryRecord(2.0, "host-001", "cpu_percent", "50", "%"),
        ]

        summary = process_records(records)

        self.assertEqual(summary.invalid_records, 3)
        self.assertEqual(summary.metrics, {})

    def test_consumes_iterable_once_and_accepts_generated_data(self):
        summary = process_records(iter_timeseries(100, seed=42))

        self.assertEqual(summary.records_seen, 100)
        self.assertEqual(summary.valid_records + summary.invalid_records, 100)
        self.assertGreater(summary.valid_records, 0)
        self.assertEqual(summary.anomaly_records,
                         sum(metric.anomalies for metric in summary.metrics.values()))

    def test_generated_series_include_threshold_anomalies(self):
        summary = process_records(iter_timeseries(500, seed=42, host_count=1,
                                                  invalid_rate=0))
        self.assertGreater(summary.anomaly_records, 0)


class RollingStatisticsTests(unittest.TestCase):
    def test_computes_bounded_window_average_and_standard_deviation(self):
        records = [TelemetryRecord(float(i), "host-001", "cpu_percent", float(i), "%")
                   for i in (1, 2, 3, 4)]

        results = list(iter_rolling_statistics(records, window_size=3, min_history=2))

        self.assertEqual([item.window_count for item in results], [1, 2, 3, 3])
        self.assertEqual(results[-1].moving_average, 3.0)
        self.assertAlmostEqual(results[-1].moving_stddev, math.sqrt(2 / 3))

    def test_flags_spike_against_prior_samples(self):
        values = [10.0, 10.0, 10.0, 100.0]
        records = [TelemetryRecord(float(i), "host-001", "cpu_percent", value, "%")
                   for i, value in enumerate(values)]

        results = list(iter_rolling_statistics(records, window_size=3,
                                                min_history=3, sigma_threshold=3))

        self.assertEqual([item.is_anomaly for item in results], [False, False, False, True])

    def test_keeps_series_separate_and_skips_invalid_rows(self):
        records = [
            TelemetryRecord(1.0, "host-001", "cpu_percent", 10.0, "%"),
            TelemetryRecord(1.0, "host-002", "cpu_percent", 80.0, "%"),
            TelemetryRecord(2.0, "", "cpu_percent", 90.0, "%"),
            TelemetryRecord(2.0, "host-001", "cpu_percent", 20.0, "%"),
        ]

        results = list(iter_rolling_statistics(records, window_size=3, min_history=2))

        self.assertEqual(results[0].moving_average, 10.0)
        self.assertEqual(results[1].moving_average, 80.0)
        self.assertFalse(results[2].is_valid)
        self.assertIsNone(results[2].moving_average)
        self.assertEqual(results[3].moving_average, 15.0)

    def test_rejects_decreasing_timestamps_in_a_series(self):
        records = [
            TelemetryRecord(2.0, "host-001", "cpu_percent", 20.0, "%"),
            TelemetryRecord(1.0, "host-001", "cpu_percent", 10.0, "%"),
        ]
        with self.assertRaises(ValueError):
            list(iter_rolling_statistics(records))

    def test_rejects_invalid_window_settings(self):
        with self.assertRaises(ValueError):
            list(iter_rolling_statistics([], window_size=0))
        with self.assertRaises(ValueError):
            list(iter_rolling_statistics([], window_size=3, min_history=4))
        with self.assertRaises(ValueError):
            list(iter_rolling_statistics([], sigma_threshold=float("nan")))


if __name__ == "__main__":
    unittest.main()
