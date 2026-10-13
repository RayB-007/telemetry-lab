# Telemetry Lab

A small, dependency-free Python tool for inspecting timestamped CSV data. It measures sampling rate, timing jitter, and gaps, then produces a JSON summary and a standalone HTML/SVG report.

Useful for checking a log before drawing conclusions about a sensor or control loop. Includes synthetic example data and checks for common timing issues.

## Run

Requires Python 3.10 or newer. No installation or network access is needed.

```sh
python3 telemetry_lab.py examples/synthetic.csv --signal position_ticks --expected-period-ms 20 --html report.html --json summary.json
```

Open `report.html` in a browser. The report includes a signal plot, interval percentiles, and gap locations. `examples/synthetic.csv` is generated demonstration data with one deliberate sampling gap; it is not a real team log.

## Input

A CSV must have `timestamp_ms` and a numeric signal column:

```csv
timestamp_ms,position_ticks
0,12
20,19
40,31
```

Timestamps must increase strictly. Missing headers, nonnumeric values, NaN, infinity, and invalid analysis options are rejected with a useful CLI error.

## How it works

- Rate uses the mean observed sample interval, including gaps.
- Percentiles use linear interpolation between sorted values.
- Jitter is the absolute difference from the expected sample period. Supply a known period; otherwise the median observed interval is used.
- A gap is an interval greater than `--gap-factor` times the expected period (default: 2).

A timing gap is an observation, not evidence of a particular hardware fault. The SVG plots all samples, so this tool is intended for modest logs rather than multi-million-row datasets.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

Tests cover exact cadence, irregular timing, gap detection, percentile interpolation, constant signals, escaped report labels, malformed CSV, and invalid options.

## Next steps

Streaming input and decimation for large logs would be useful additions. Real hardware validation has not been performed.

## Portfolio

More projects and background: [rayansh.dev](https://rayansh.dev/projects/).
