import tempfile
import unittest
from pathlib import Path
from telemetry_lab import analyze, load_csv, percentile, report_html

class TelemetryTests(unittest.TestCase):
    def test_exact_cadence(self):
        result = analyze([(0, 1), (20, 2), (40, 3)])
        self.assertEqual(result['observed_rate_hz'], 50)
        self.assertEqual(result['jitter_p95_ms'], 0)
        self.assertEqual(result['gaps'], [])

    def test_gap_and_explicit_period(self):
        result = analyze([(0, 1), (20, 2), (100, 3)], 20)
        self.assertEqual(result['gaps'], [{'after_sample': 1, 'interval_ms': 80}])
        self.assertEqual(result['period_source'], 'explicit')

    def test_interpolated_percentile(self):
        self.assertEqual(percentile([30, 0, 20, 10], .5), 15)
        self.assertAlmostEqual(percentile([30, 0, 20, 10], .95), 28.5)

    def test_rejects_nonmonotonic_timestamps(self):
        with self.assertRaises(ValueError): analyze([(10, 1), (10, 2)])
        with self.assertRaises(ValueError): analyze([(10, 1), (0, 2)])

    def test_rejects_invalid_options(self):
        for period in [0, -1, float('nan')]:
            with self.assertRaises(ValueError): analyze([(0, 1), (10, 2)], period)
        with self.assertRaises(ValueError): analyze([(0, 1), (10, 2)], gap_factor=1)

    def test_constant_negative_signal_and_html_escaping(self):
        points = [(0, -10), (20, -10)]
        report = report_html(points, analyze(points), '<script>')
        self.assertIn('40.00,130', report)
        self.assertNotIn('<script>', report)
        self.assertIn('&lt;script&gt;', report)

    def test_csv_invalid_values_and_headers(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'log.csv'
            for text in ['timestamp_ms,position_ticks\n0,NaN\n20,1', 'time,x\n0,1\n1,2', 'timestamp_ms,position_ticks\n0,nope\n20,1']:
                path.write_text(text)
                with self.assertRaises(ValueError): load_csv(path, 'position_ticks')
            path.write_text('timestamp_ms,position_ticks\n0,1\n20,2\n')
            self.assertEqual(load_csv(path, 'position_ticks'), [(0, 1), (20, 2)])

if __name__ == '__main__': unittest.main()
