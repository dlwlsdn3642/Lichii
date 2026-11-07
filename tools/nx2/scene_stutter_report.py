#!/usr/bin/env python3
"""Correlate opt-in Lichii scene-stutter events by their log timestamps."""

import argparse
from dataclasses import dataclass
from pathlib import Path
import re


TIME = re.compile(r"^\[(\d+(?:\.\d+)?)\]")
EVENTS = {
    "guest": re.compile(r"Scene stutter guest present: frame=(\d+) gap_ms=([\d.]+)"),
    "host": re.compile(r"Scene stutter host present: id=(\d+) gap_ms=([\d.]+)"),
    "shader": re.compile(
        r"Scene stutter shader translation: pipeline=([0-9a-fA-F]+) "
        r"stage=(\d+) shader=([0-9a-fA-F]+) time_ms=([\d.]+)"
    ),
    "pipeline_wait": re.compile(
        r"Scene stutter pipeline wait: pipeline=([0-9a-fA-F]+) time_ms=([\d.]+)"
    ),
    "cpu_readback": re.compile(
        r"Scene stutter CPU readback: address=(0x[0-9a-fA-F]+) "
        r"size=(\d+) time_ms=([\d.]+)"
    ),
    "runtime_pipeline": re.compile(
        r"(?:Graphics|Compute) pipeline built on the GPU thread in "
        r"([\d.]+) ms: (pipeline=[0-9a-fA-F]+)"
    ),
}


@dataclass(frozen=True)
class Event:
    time: float
    kind: str
    duration_ms: float
    detail: str


def parse_line(line: str) -> Event | None:
    stamp = TIME.match(line)
    if stamp is None:
        return None
    time = float(stamp.group(1))
    for kind, pattern in EVENTS.items():
        match = pattern.search(line)
        if match is None:
            continue
        if kind in ("guest", "host"):
            return Event(time, kind, float(match.group(2)), match.group(1))
        if kind == "shader":
            return Event(
                time, kind, float(match.group(4)),
                f"pipeline={match.group(1)} stage={match.group(2)} shader={match.group(3)}",
            )
        if kind == "pipeline_wait":
            return Event(time, kind, float(match.group(2)), f"pipeline={match.group(1)}")
        if kind == "runtime_pipeline":
            return Event(time, kind, float(match.group(1)), match.group(2))
        return Event(time, kind, float(match.group(3)), f"address={match.group(1)}")
    return None


def read_events(path: Path) -> list[Event]:
    events = []
    with path.open("r", encoding="utf-8-sig", errors="replace") as log:
        for line in log:
            event = parse_line(line)
            if event is not None:
                events.append(event)
    return events


def related_events(events: list[Event], gap: Event, margin_ms: float = 100) -> list[Event]:
    """A present gap spans the period before its timestamp, not after it."""
    start = gap.time - gap.duration_ms / 1000 - margin_ms / 1000
    end = gap.time + margin_ms / 1000
    return [
        event for event in events
        if event.kind not in ("guest", "host")
        and start <= event.time <= end
    ]


def render(events: list[Event], min_ms: float, limit: int) -> str:
    gaps = sorted(
        (event for event in events
         if event.kind in ("guest", "host") and event.duration_ms >= min_ms),
        key=lambda item: item.duration_ms,
        reverse=True,
    )
    if not gaps:
        slow = sorted(
            (event for event in events if event.kind not in ("guest", "host")),
            key=lambda item: item.duration_ms,
            reverse=True,
        )[:limit]
        if not slow:
            return "No scene-stutter events found. Enable EDEN_NX2_STUTTER_TRACE=1."
        return "No long present gaps recorded; slow work:\n" + "\n".join(
            f"  [{e.time:.3f}s] {e.kind} {e.duration_ms:.1f} ms {e.detail}"
            for e in slow
        )
    lines = [f"Top {min(limit, len(gaps))} present gaps (potential causes are temporal matches):"]
    for gap in gaps[:limit]:
        label = "frame" if gap.kind == "guest" else "present id"
        lines.append(
            f"[{gap.time:.3f}s] {gap.kind} {label}={gap.detail}: {gap.duration_ms:.1f} ms"
        )
        near = sorted(
            related_events(events, gap),
            key=lambda item: item.duration_ms,
            reverse=True,
        )
        for event in near[:5]:
            lines.append(
                f"  [{event.time:.3f}s] {event.kind}: "
                f"{event.duration_ms:.1f} ms {event.detail}"
            )
        if not near:
            lines.append("  No shader/pipeline/readback event in the matching time window.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="eden_log.txt from a stuttering session")
    parser.add_argument("--min-ms", type=float, default=50)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if args.min_ms <= 0 or args.limit <= 0:
        parser.error("--min-ms and --limit must be positive")
    print(render(read_events(args.log), args.min_ms, args.limit))


if __name__ == "__main__":
    main()