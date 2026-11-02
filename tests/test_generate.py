import json
import unittest
from io import StringIO

from telemetry_engine.generate import iter_records, iter_timeseries, write_jsonl


class GenerateRecordsTests(unittest.TestCase):
    def test_count_and_seed_are_reproducible(self):
        first = list(iter_records(20, seed=42))
        second = list(iter_records(20, seed=42))
        self.assertEqual(len(first), 20)
        self.assertEqual(first, second)

    def test_invalid_rate_controls_invalid_records(self):
        self.assertTrue(all(r.host_id and r.value is not None
                            for r in iter_records(10, invalid_rate=0)))
        self.assertTrue(all(not r.host_id or r.value is None
                            for r in iter_records(10, invalid_rate=1)))

    def test_rejects_invalid_arguments(self):
        with self.assertRaises(ValueError):
            list(iter_records(-1))
        with self.assertRaises(ValueError):
            list(iter_records(1, invalid_rate=1.1))

    def test_writes_json_lines(self):
        output = StringIO()
        written = write_jsonl(iter_records(3, invalid_rate=0), output)
        lines = output.getvalue().splitlines()
        self.assertEqual(written, 3)
        self.assertEqual(len(lines), 3)
        self.assertEqual(json.loads(lines[0])["metric"], "disk_read_mbps")

    def test_timeseries_is_reproducible_and_regular_per_host_metric(self):
        first = list(iter_timeseries(32, seed=42, host_count=2, invalid_rate=0,
                                     sample_interval_seconds=5))
        second = list(iter_timeseries(32, seed=42, host_count=2, invalid_rate=0,
                                      sample_interval_seconds=5))
        self.assertEqual(first, second)

        grouped = {}
        for record in first:
            grouped.setdefault((record.host_id, record.metric), []).append(record.timestamp)
        self.assertEqual(len(grouped), 8)
        for timestamps in grouped.values():
            self.assertEqual(len(timestamps), 4)
            self.assertEqual([b - a for a, b in zip(timestamps, timestamps[1:])], [5, 5, 5])

    def test_timeseries_invalid_rate_controls_invalid_records(self):
        self.assertTrue(all(r.host_id and r.value is not None
                            for r in iter_timeseries(20, invalid_rate=0)))
        self.assertTrue(all(not r.host_id or r.value is None
                            for r in iter_timeseries(20, invalid_rate=1)))

    def test_timeseries_rejects_invalid_arguments(self):
        with self.assertRaises(ValueError):
            list(iter_timeseries(10, host_count=0))
        with self.assertRaises(ValueError):
            list(iter_timeseries(10, sample_interval_seconds=0))


if __name__ == "__main__":
    unittest.main()
