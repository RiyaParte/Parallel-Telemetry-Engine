import math
import unittest

from telemetry_engine import TelemetryRecord, iter_records, process_records


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
        summary = process_records(iter_records(100, seed=42))

        self.assertEqual(summary.records_seen, 100)
        self.assertEqual(summary.valid_records + summary.invalid_records, 100)
        self.assertGreater(summary.valid_records, 0)
        self.assertEqual(summary.anomaly_records,
                         sum(metric.anomalies for metric in summary.metrics.values()))


if __name__ == "__main__":
    unittest.main()
