#!/usr/bin/env python3
"""Offline CSV telemetry inspection. Standard library only."""
import argparse
import csv
import html
import json
import math
from pathlib import Path
import statistics


def percentile(values, fraction):
    if not values or not 0 <= fraction <= 1:
        raise ValueError('Percentile needs data and a fraction between 0 and 1')
    ordered = sorted(values)
    index = fraction * (len(ordered) - 1)
    low, high = math.floor(index), math.ceil(index)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def load_csv(path, signal):
    with Path(path).open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or 'timestamp_ms' not in reader.fieldnames or signal not in reader.fieldnames:
            raise ValueError(f'CSV requires timestamp_ms and {signal} columns')
        points = []
        for line, row in enumerate(reader, 2):
            try:
                point = (float(row['timestamp_ms']), float(row[signal]))
            except (ValueError, TypeError) as error:
                raise ValueError(f'Invalid numeric value on line {line}') from error
            if not all(math.isfinite(value) for value in point):
                raise ValueError(f'Non-finite value on line {line}')
            if points and point[0] <= points[-1][0]:
                raise ValueError(f'Timestamps must increase strictly (line {line})')
            points.append(point)
    if len(points) < 2:
        raise ValueError('At least two samples are required')
    return points


def analyze(points, expected_period=None, gap_factor=2):
    if len(points) < 2 or any(not all(math.isfinite(v) for v in p) for p in points):
        raise ValueError('At least two finite samples are required')
    intervals = [b[0] - a[0] for a, b in zip(points, points[1:])]
    if any(value <= 0 for value in intervals):
        raise ValueError('Timestamps must increase strictly')
    target = statistics.median(intervals) if expected_period is None else expected_period
    if not math.isfinite(target) or target <= 0 or not math.isfinite(gap_factor) or gap_factor <= 1:
        raise ValueError('Expected period must be positive and gap factor greater than 1')
    gaps = [{'after_sample': i, 'interval_ms': value} for i, value in enumerate(intervals) if value > target * gap_factor]
    signal = [p[1] for p in points]
    return {
        'samples': len(points), 'duration_ms': points[-1][0] - points[0][0],
        'observed_rate_hz': 1000 / statistics.mean(intervals),
        'expected_period_ms': target, 'period_source': 'median' if expected_period is None else 'explicit',
        'interval_p50_ms': percentile(intervals, .5), 'interval_p95_ms': percentile(intervals, .95),
        'jitter_p95_ms': percentile([abs(value - target) for value in intervals], .95),
        'gap_threshold_ms': target * gap_factor, 'gaps': gaps, 'signal_min': min(signal), 'signal_max': max(signal), 'signal_mean': statistics.mean(signal),
    }


def report_html(points, result, signal):
    # The plot stays within its frame for negative, constant, or tiny-range signals.
    start, end = points[0][0], points[-1][0]
    low, high = min(p[1] for p in points), max(p[1] for p in points)
    coordinates = ' '.join(f'{40 + 720 * (t-start)/(end-start):.2f},{220 - 180 * (v-low)/(high-low):.2f}'
                           if high != low else f'{40 + 720 * (t-start)/(end-start):.2f},130' for t, v in points)
    title = html.escape(signal)
    cards = ''.join(f'<dt>{html.escape(key.replace("_", " "))}</dt><dd>{value:.3f}</dd>'
                    for key, value in result.items() if isinstance(value, (float, int)))
    gaps = ''.join(f'<li>After sample {g["after_sample"]}: {g["interval_ms"]:.2f} ms</li>' for g in result['gaps']) or '<li>No gaps above the configured threshold.</li>'
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Telemetry Lab · {title}</title>
<style>body{{font:16px/1.6 system-ui;max-width:900px;margin:40px auto;padding:0 20px;background:#101620;color:#e2e8f0}}svg{{width:100%;background:#182332;border-radius:10px}}dl{{display:grid;grid-template-columns:1fr 1fr}}dt{{color:#a2b4ca}}dd{{margin:0;text-align:right}}polyline{{fill:none;stroke:#57dfd1;stroke-width:2}}text{{fill:#a2b4ca;font-size:12px}}</style>
<h1>Telemetry Lab</h1><p>Signal: {title}. Offline analysis; no network requests.</p>
<svg viewBox="0 0 800 270" role="img" aria-label="{title} over time"><path d="M40 40V230H760" stroke="#52647c" fill="none"/><polyline points="{coordinates}"/><text x="40" y="255">{start:g} ms</text><text x="680" y="255">{end:g} ms</text></svg>
<dl>{cards}</dl><h2>Sampling gaps</h2><p>Threshold: more than {result['gap_threshold_ms']:g} ms.</p><ul>{gaps}</ul>
<p>Timing gaps are observations, not diagnoses of a sensor or control loop.</p></html>'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--signal', default='position_ticks')
    parser.add_argument('--expected-period-ms', type=float)
    parser.add_argument('--gap-factor', type=float, default=2)
    parser.add_argument('--html', type=Path, help='Write a standalone SVG/HTML report')
    parser.add_argument('--json', type=Path, help='Write a JSON summary')
    args = parser.parse_args(argv)
    try:
        points = load_csv(args.csv, args.signal)
        result = analyze(points, args.expected_period_ms, args.gap_factor)
        encoded = json.dumps(result, indent=2, allow_nan=False) + '\n'
        if args.json: args.json.write_text(encoded)
        if args.html: args.html.write_text(report_html(points, result, args.signal))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(encoded, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
