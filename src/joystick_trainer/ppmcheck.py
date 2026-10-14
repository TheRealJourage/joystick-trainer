import argparse
import csv
import statistics


def load_edges(path):
    """Transitions as (time_s, level). Accepts 'time,level' CSV rows; a header row is skipped."""
    edges = []
    with open(path, newline="") as handle:
        for row in csv.reader(handle):
            try:
                edges.append((float(row[0]), int(float(row[1]))))
            except (ValueError, IndexError):
                continue
    return edges


def analyze(edges, active_high=True):
    """Split edges into frames at the sync gap and report widths in microseconds."""
    starts = [t for t, level in edges if level == (1 if active_high else 0)]
    ends = [t for t, level in edges if level == (0 if active_high else 1)]
    pulses = []
    for start in starts:
        end = next((e for e in ends if e > start), None)
        if end is not None:
            pulses.append((start, (end - start) * 1e6))
    periods = [(b[0] - a[0]) * 1e6 for a, b in zip(pulses, pulses[1:])]
    if not periods:
        return None
    sync_threshold = 3000
    frames, current = [], []
    for period in periods:
        if period >= sync_threshold:
            if current:
                frames.append(current)
            current = []
        else:
            current.append(period)
    if current:
        frames.append(current)
    if not frames:
        return None
    channel_count = statistics.mode(len(f) for f in frames)
    complete = [f for f in frames if len(f) == channel_count]
    result = {
        "frames": len(frames),
        "complete_frames": len(complete),
        "channels": channel_count,
        "pulse_us_mean": statistics.mean(width for _, width in pulses),
        "pulse_us_stdev": statistics.pstdev(width for _, width in pulses),
        "frame_us_mean": None,
        "per_channel": [],
    }
    frame_lengths = [sum(f) + p for f, p in zip(complete, [p for p in periods if p >= sync_threshold][1:])] if len(complete) > 1 else []
    if frame_lengths:
        result["frame_us_mean"] = statistics.mean(frame_lengths)
        result["frame_us_stdev"] = statistics.pstdev(frame_lengths)
    for i in range(channel_count):
        values = [f[i] for f in complete]
        result["per_channel"].append(
            {"channel": i + 1, "mean_us": statistics.mean(values), "stdev_us": statistics.pstdev(values),
             "min_us": min(values), "max_us": max(values)}
        )
    return result


def report(result):
    if result is None:
        return "no PPM frames found"
    lines = [f"frames: {result['frames']} ({result['complete_frames']} complete), channels: {result['channels']}",
             f"pulse: {result['pulse_us_mean']:.1f} us (stdev {result['pulse_us_stdev']:.1f})"]
    if result["frame_us_mean"]:
        lines.append(f"frame: {result['frame_us_mean']:.0f} us (stdev {result['frame_us_stdev']:.1f})")
    for c in result["per_channel"]:
        lines.append(f"ch{c['channel']}: {c['mean_us']:.0f} us  stdev {c['stdev_us']:.1f}  range {c['min_us']:.0f}-{c['max_us']:.0f}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(prog="ppmcheck")
    parser.add_argument("csv", help="logic analyzer export with transitions: time_seconds,level")
    parser.add_argument("--active-low", action="store_true")
    args = parser.parse_args()
    print(report(analyze(load_edges(args.csv), active_high=not args.active_low)))
