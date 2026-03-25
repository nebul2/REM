#!/usr/bin/env python3
"""
Measure TP-Link poll round duration vs collector_control settings.

Effective per-device sample spacing ≈ round_duration + poll_interval (sleep after each cycle).

Run inside the collector container (needs TOKEN_FILE, CONF_FILE, COLLECTOR_CONTROL_FILE):

  docker compose exec collector python /app/benchmark_poll_cycle.py --rounds 5
  docker compose exec collector python /app/benchmark_poll_cycle.py --sweep --rounds 3
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("benchmark")

# Import after path setup (collector lives in /app)
import collector as col


def _read_control():
    path = col.COLLECTOR_CONTROL_FILE
    control = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                control = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Could not read %s: %s", path, e)
    delay = float(control.get("device_query_delay", 0.5))
    poll_interval = None
    pi = control.get("poll_interval")
    if pi is not None:
        try:
            v = int(pi)
            if 5 <= v <= 300:
                poll_interval = v
        except (TypeError, ValueError):
            pass
    return control, delay, poll_interval


def _one_full_cycle(access_token, parallel_workers, device_query_delay):
    """Wall-clock time for getDeviceList (+) collect_power_readings."""
    t0 = time.perf_counter()
    device_id_list = col.getDeviceIdList(access_token)
    list_dt = time.perf_counter() - t0
    if not device_id_list:
        return {
            "total": time.perf_counter() - t0,
            "list_sec": list_dt,
            "poll_sec": 0.0,
            "devices": 0,
            "ok": 0,
            "failed": 0,
        }
    t1 = time.perf_counter()
    points, failed = col.collect_power_readings(
        device_id_list, access_token, parallel_workers, device_query_delay
    )
    poll_dt = time.perf_counter() - t1
    return {
        "total": time.perf_counter() - t0,
        "list_sec": list_dt,
        "poll_sec": poll_dt,
        "devices": len(device_id_list),
        "ok": len(points),
        "failed": len(failed),
    }


def _run_series(
    access_token,
    parallel_workers,
    device_query_delay,
    rounds: int,
):
    rows = []
    for i in range(rounds):
        row = _one_full_cycle(
            access_token, parallel_workers, device_query_delay
        )
        row["round"] = i + 1
        rows.append(row)
        logger.info(
            "Round %s/%s: total=%.2fs (list=%.2fs poll=%.2fs) devices=%s ok=%s failed=%s",
            i + 1,
            rounds,
            row["total"],
            row["list_sec"],
            row["poll_sec"],
            row["devices"],
            row["ok"],
            row["failed"],
        )
    return rows


def _summarize(rows, poll_interval: int | None, target_cadence: float):
    totals = [r["total"] for r in rows]
    mean_total = statistics.mean(totals)
    stdev = statistics.stdev(totals) if len(totals) > 1 else 0.0
    pi = poll_interval if poll_interval is not None else 30
    effective = mean_total + pi
    return {
        "mean_round_sec": mean_total,
        "stdev_round_sec": stdev,
        "min_round_sec": min(totals),
        "max_round_sec": max(totals),
        "poll_interval_sec": pi,
        "effective_cadence_sec": effective,
        "target_cadence_sec": target_cadence,
        "meets_target": effective <= target_cadence + 0.5,
    }


def _print_recommendation(stats: dict, best_workers: int | None):
    print()
    print("=== Summary ===")
    print(
        f"Mean round time (list + all device polls): {stats['mean_round_sec']:.2f}s "
        f"(σ={stats['stdev_round_sec']:.2f}s, min={stats['min_round_sec']:.2f}s, max={stats['max_round_sec']:.2f}s)"
    )
    print(
        f"Poll interval (sleep after each round, from control): {stats['poll_interval_sec']}s"
    )
    print(
        f"Effective per-device sample spacing ≈ round + sleep: {stats['effective_cadence_sec']:.2f}s"
    )
    tgt = stats["target_cadence_sec"]
    print(f"Target cadence: {tgt:.0f}s")
    if stats["meets_target"]:
        print("✓ Effective cadence is within target (±0.5s).")
    else:
        print(
            "✗ Effective cadence exceeds target. Options: raise parallel_workers, "
            "lower device_query_delay (if API stays stable), or reduce poll_interval "
            "toward the minimum (5s) if the UI allows."
        )
    # poll_interval valid range matches collector (5–300)
    mr = stats["mean_round_sec"]
    ideal_sleep = round(tgt - mr)
    if ideal_sleep < 5:
        print(
            f"  To reach ~{tgt:.0f}s spacing, you need round + poll_interval ≤ {tgt:.0f}s. "
            f"With mean round ≈ {mr:.1f}s, minimum poll_interval is 5s → "
            f"effective cadence ≈ {mr + 5:.1f}s (shorten the round by increasing workers "
            f"or lowering inter-chunk delay)."
        )
    elif ideal_sleep <= 300:
        print(
            f"  Hint: poll_interval ≈ {ideal_sleep}s would give ~{mr + ideal_sleep:.1f}s "
            f"effective cadence (round + sleep)."
        )
    if best_workers is not None:
        print(f"Suggested parallel_workers (fastest mean round in sweep): {best_workers}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark TP-Link poll rounds (no DB writes)."
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=5,
        help="Full cycles per configuration (default 5)",
    )
    parser.add_argument(
        "--target-cadence",
        type=float,
        default=10.0,
        help="Desired seconds between samples per device (default 10)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Override parallel workers (default: control file / env)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Override device_query_delay seconds (default: control file)",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Try several worker counts and pick the fastest stable mean round time",
    )
    parser.add_argument(
        "--sweep-list",
        type=str,
        default="1,2,4,6,8,10,12,16",
        help="Comma-separated worker counts for --sweep",
    )
    args = parser.parse_args()

    control, default_delay, poll_interval = _read_control()
    device_query_delay = (
        float(args.delay) if args.delay is not None else default_delay
    )

    if args.workers is not None:
        parallel_workers = max(1, min(32, int(args.workers)))
    else:
        parallel_workers = col._parse_parallel_workers(control)

    print("=== TP-Link poll benchmark (no DB writes) ===")
    print(f"COLLECTOR_CONTROL_FILE={col.COLLECTOR_CONTROL_FILE}")
    print(
        f"device_query_delay={device_query_delay}s  "
        f"poll_interval(from file)={poll_interval}  "
        f"workers={parallel_workers}"
    )
    print()

    try:
        access_token = col.getToken()
    except Exception as e:
        logger.error("Token failed: %s", e)
        sys.exit(1)

    if args.sweep:
        counts = []
        for part in args.sweep_list.split(","):
            part = part.strip()
            if not part:
                continue
            counts.append(max(1, min(32, int(part))))
        counts = sorted(set(counts))
        if not counts:
            logger.error("No worker counts parsed from --sweep-list")
            sys.exit(1)

        best_w = None
        best_mean = None
        best_rows = None
        results = []

        for w in counts:
            print(f"--- Sweep: parallel_workers={w} ---")
            rows = _run_series(
                access_token, w, device_query_delay, args.rounds
            )
            stats = _summarize(rows, poll_interval, args.target_cadence)
            stats["workers"] = w
            results.append(stats)
            print(
                f"  mean_round={stats['mean_round_sec']:.2f}s  "
                f"effective_cadence≈{stats['effective_cadence_sec']:.2f}s  "
                f"meets_target={stats['meets_target']}"
            )
            if best_mean is None or stats["mean_round_sec"] < best_mean:
                best_mean = stats["mean_round_sec"]
                best_w = w
                best_rows = rows

        if best_rows is not None and best_w is not None:
            stats_final = _summarize(best_rows, poll_interval, args.target_cadence)
            _print_recommendation(stats_final, best_w)
        print("Sweep table (workers → mean round s → effective cadence s):")
        for s in results:
            print(
                f"  {s['workers']:2d}  {s['mean_round_sec']:6.2f}  {s['effective_cadence_sec']:6.2f}"
            )
        return

    rows = _run_series(
        access_token, parallel_workers, device_query_delay, args.rounds
    )
    stats = _summarize(rows, poll_interval, args.target_cadence)
    _print_recommendation(stats, None)


if __name__ == "__main__":
    main()
