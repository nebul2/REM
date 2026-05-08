#!/usr/bin/env python3
"""
Overnight polling validity diagnostic for the GOS REM fleet.

Phases (sequential, 10-min cooldown between each):
  1. Fleet audit (15 min) — sample getDeviceList every 30s, identify always-online supported devices
  2. 4 healthy devices, 1h, poll_interval=10s
  3. 8 healthy devices, 1h, poll_interval=10s
  4. 12 healthy devices, 1h, poll_interval=10s

Safety:
  - Hard cap on total API calls (CALL_BUDGET).
  - Per-phase abort if rate-limit fraction over last 5 cycles > RATE_LIMIT_FRACTION_ABORT.
  - Kill switch: touch /tmp/abort-poll-test
  - Each phase writes its own CSV; partial data preserved on abort.

Run inside stats-collector container:
  docker exec -d stats-collector python /app/poll_validity_test.py

Outputs: /app/data/diagnostics/{audit_fleet, validity_4dev, validity_8dev, validity_12dev}.csv
"""
from __future__ import annotations

import csv
import os
import sys
import time
import json
from collections import defaultdict

# Reuse production collector's primitives.
import collector as col

OUTPUT_DIR = "/app/data/diagnostics"
ABORT_FILE = "/tmp/abort-poll-test"
LOG_FILE = f"{OUTPUT_DIR}/run.log"

# Safety
CALL_BUDGET = 12000
RATE_LIMIT_FRACTION_ABORT = 0.30  # abort phase if >30% of calls in last 5 cycles were rate-limited
COOLDOWN_BETWEEN_PHASES = 600  # 10 min, no API calls

# State
_total_calls = 0


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def check_abort(reason: str = "") -> None:
    if os.path.exists(ABORT_FILE):
        log(f"ABORT signal detected ({reason}); exiting cleanly")
        sys.exit(0)
    if _total_calls > CALL_BUDGET:
        log(f"CALL BUDGET ({CALL_BUDGET}) exceeded ({_total_calls}); aborting to protect TP-Link relationship")
        sys.exit(1)


def cooldown(seconds: int, label: str) -> None:
    log(f"COOLDOWN {seconds}s ({label}); no API calls")
    end = time.time() + seconds
    while time.time() < end:
        check_abort(reason=f"cooldown {label}")
        time.sleep(min(30, max(1, end - time.time())))


def run_audit(duration_sec: int = 900, sample_interval: int = 30,
              output_path: str = f"{OUTPUT_DIR}/audit_fleet.csv") -> list[dict]:
    """
    Phase 1: call getDeviceList every sample_interval seconds for duration_sec.
    Record online flag per device per sample. Return list of always-online supported devices.
    """
    global _total_calls
    log(f"AUDIT START: duration={duration_sec}s, sample_interval={sample_interval}s")

    access_token = col.getToken()
    samples = []  # (ts, device_id, alias, model, online)

    end = time.time() + duration_sec
    sample_count = 0
    import requests
    while time.time() < end:
        check_abort("audit")
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            resp = requests.post(
                "https://aps1-openapi.tplinknbu.com/v1/getDeviceList?",
                data={
                    "client_id": "fdcae128-0adf-4233-8a58-30760652bd16",
                    "api_key": "e71bf02f-8b71-42ee-8af0-62a7bdf6c866",
                    "token": access_token,
                },
                timeout=15,
            )
            _total_calls += 1
            data = resp.json()
            devices = data.get("devices") or []
            for dev in devices:
                samples.append((
                    ts,
                    dev.get("deviceId"),
                    dev.get("alias"),
                    dev.get("model"),
                    bool(dev.get("online", False)),
                ))
            sample_count += 1
            online_now = sum(1 for d in devices if d.get("online"))
            log(f"  audit sample {sample_count}: {len(devices)} reported, {online_now} online")
        except Exception as e:
            log(f"  audit sample error: {e}")
        time.sleep(sample_interval)

    # Write CSV (raw samples)
    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_utc", "device_id", "alias", "model", "online"])
            writer.writerows(samples)
        log(f"  audit CSV written: {output_path} ({len(samples)} rows)")
    except OSError as e:
        log(f"  could not write audit CSV: {e}")

    # Categorise per device
    online_count = defaultdict(int)
    total_count = defaultdict(int)
    metadata = {}
    for ts, did, alias, model, online in samples:
        if did is None:
            continue
        total_count[did] += 1
        if online:
            online_count[did] += 1
        metadata[did] = (alias, model)

    healthy = []  # always-online + supported model
    flapping = []  # sometimes-online + supported model
    dead = []  # never-online
    unsupported = []  # supported model filter excluded

    for did, total in total_count.items():
        alias, model = metadata[did]
        frac = online_count[did] / total if total > 0 else 0
        item = {"deviceId": did, "alias": alias, "model": model, "online_fraction": frac}
        if model not in col.SUPPORTED_ENERGY_MODELS:
            unsupported.append(item)
        elif frac == 1.0:
            healthy.append(item)
        elif frac == 0.0:
            dead.append(item)
        else:
            flapping.append(item)

    log(f"AUDIT END: {sample_count} samples · {len(healthy)} always-online supported · "
        f"{len(flapping)} flapping · {len(dead)} never-online · {len(unsupported)} unsupported model")
    log(f"  healthy aliases: {[h['alias'] for h in healthy]}")
    if flapping:
        log(f"  flapping (alias, online_fraction): {[(d['alias'], round(d['online_fraction'], 2)) for d in flapping]}")
    if dead:
        log(f"  dead/offline whole window: {[d['alias'] for d in dead]}")

    # Write summary CSV
    summary_path = output_path.replace(".csv", "_summary.csv")
    try:
        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["category", "device_id", "alias", "model", "online_fraction"])
            for cat, lst in [("healthy", healthy), ("flapping", flapping), ("dead", dead), ("unsupported", unsupported)]:
                for d in lst:
                    writer.writerow([cat, d["deviceId"], d["alias"], d["model"], round(d["online_fraction"], 3)])
        log(f"  audit summary CSV: {summary_path}")
    except OSError as e:
        log(f"  could not write audit summary: {e}")

    # Sort healthy by alias for stable selection across re-runs
    healthy.sort(key=lambda d: d["alias"] or "")
    return healthy


def run_validity_test(devices: list[dict], label: str, duration_sec: int = 3600,
                      poll_interval: int = 10, parallel_workers: int | None = None,
                      output_path: str = "") -> dict:
    """
    Poll the given devices every poll_interval seconds for duration_sec.
    parallel_workers defaults to len(devices) (one chunk = fastest).
    Mirrors production collector cadence: cycle = round_duration + poll_interval.
    """
    global _total_calls
    if parallel_workers is None:
        parallel_workers = max(1, min(32, len(devices)))

    log(f"VALIDITY {label} START: {len(devices)} devices, poll_interval={poll_interval}s, "
        f"parallel_workers={parallel_workers}, duration={duration_sec}s")
    log(f"  devices: {[d['alias'] for d in devices]}")

    access_token = col.getToken()
    rows = []
    rate_hits_recent = []  # last 5 cycles
    cycle = 0
    start = time.time()
    end = start + duration_sec

    fieldnames = ["timestamp_utc", "cycle", "device_alias", "success", "power_w",
                  "round_duration_s", "rate_limit_hits_this_cycle", "error"]
    # Write header up front so partial data is well-formed
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=fieldnames).writeheader()

    while time.time() < end:
        check_abort(label)
        cycle += 1
        cycle_start = time.time()
        col.reset_rate_limit_hits()

        try:
            points, failed = col.collect_power_readings(
                devices, access_token, parallel_workers, 0.5
            )
            _total_calls += len(devices)
        except col.TokenInvalidError:
            log(f"  cycle {cycle}: token invalid, refreshing")
            try:
                access_token = col.getToken()
            except Exception as e:
                log(f"  token refresh failed: {e}; aborting phase")
                break
            continue
        except Exception as e:
            log(f"  cycle {cycle} ERROR: {e}")
            time.sleep(poll_interval)
            continue

        round_dur = time.time() - cycle_start
        rate_hits = col.get_rate_limit_hits()
        rate_hits_recent.append(rate_hits)
        if len(rate_hits_recent) > 5:
            rate_hits_recent.pop(0)

        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        cycle_rows = []
        for p in points:
            cycle_rows.append({
                "timestamp_utc": ts, "cycle": cycle,
                "device_alias": p["alias"], "success": 1,
                "power_w": p["power_watts"], "round_duration_s": round(round_dur, 3),
                "rate_limit_hits_this_cycle": rate_hits, "error": "",
            })
        for alias in failed:
            cycle_rows.append({
                "timestamp_utc": ts, "cycle": cycle,
                "device_alias": alias, "success": 0,
                "power_w": "", "round_duration_s": round(round_dur, 3),
                "rate_limit_hits_this_cycle": rate_hits, "error": "no_reading",
            })

        # Append to CSV (don't keep all rows in memory)
        with open(output_path, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=fieldnames).writerows(cycle_rows)
        rows.extend(cycle_rows)

        # Periodic progress log
        if cycle % 30 == 0 or cycle == 1:
            log(f"  cycle {cycle}: round={round_dur:.2f}s, ok={len(points)}/{len(devices)}, "
                f"rate_hits={rate_hits}, total_api_calls={_total_calls}")

        # Safety: abort if recent rate-limit fraction is high
        if len(rate_hits_recent) >= 5:
            recent_total_calls = 5 * len(devices)
            recent_rate_hits = sum(rate_hits_recent)
            if recent_rate_hits / recent_total_calls > RATE_LIMIT_FRACTION_ABORT:
                log(f"  ABORT phase: rate-limit fraction last 5 cycles = "
                    f"{recent_rate_hits}/{recent_total_calls} = "
                    f"{recent_rate_hits/recent_total_calls:.1%} (threshold {RATE_LIMIT_FRACTION_ABORT:.0%})")
                break

        time.sleep(poll_interval)

    # Phase summary
    succ = sum(1 for r in rows if r["success"])
    fail = sum(1 for r in rows if not r["success"])
    total = succ + fail
    succ_rate = succ / total if total > 0 else 0
    avg_round = sum(r["round_duration_s"] for r in rows) / total if total > 0 else 0
    summary = {
        "label": label, "cycles": cycle, "successes": succ, "failures": fail,
        "success_rate": succ_rate, "avg_round_s": avg_round,
        "elapsed_s": time.time() - start,
    }
    log(f"VALIDITY {label} END: {cycle} cycles · {succ}/{total} reads ok · "
        f"success_rate={succ_rate:.1%} · avg_round={avg_round:.2f}s · elapsed={summary['elapsed_s']:.0f}s")

    # Per-device summary
    per_dev = defaultdict(lambda: {"ok": 0, "fail": 0})
    for r in rows:
        if r["success"]:
            per_dev[r["device_alias"]]["ok"] += 1
        else:
            per_dev[r["device_alias"]]["fail"] += 1
    log(f"  per-device summary ({label}):")
    for alias, c in sorted(per_dev.items()):
        total_d = c["ok"] + c["fail"]
        log(f"    {alias}: {c['ok']}/{total_d} = {c['ok']/total_d*100:.1f}% success")

    return summary


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # Truncate log at start so this run is its own
    open(LOG_FILE, "w").close()

    log("==== POLL VALIDITY DIAGNOSTIC START ====")
    log(f"Output dir: {OUTPUT_DIR}")
    log(f"Kill switch: touch {ABORT_FILE}")
    log(f"Total call budget: {CALL_BUDGET}")

    # Phase 1: Fleet audit
    healthy = run_audit(duration_sec=900, sample_interval=30)

    if len(healthy) < 4:
        log(f"ERROR: only {len(healthy)} healthy devices; cannot run validity tests")
        sys.exit(1)

    cooldown(COOLDOWN_BETWEEN_PHASES, "after audit")

    # Phase 2-4: validity tests with 4, 8, 12 devices
    for label, n in [("4dev", 4), ("8dev", 8), ("12dev", 12)]:
        if len(healthy) < n:
            log(f"SKIP phase {label}: only {len(healthy)} healthy devices available (need {n})")
            continue
        devices = healthy[:n]
        path = f"{OUTPUT_DIR}/validity_{label}.csv"
        run_validity_test(devices, label, duration_sec=3600, poll_interval=10, output_path=path)
        if n != 12:
            cooldown(COOLDOWN_BETWEEN_PHASES, f"after {label}")

    log("==== POLL VALIDITY DIAGNOSTIC COMPLETE ====")
    log(f"Total API calls used: {_total_calls} / budget {CALL_BUDGET}")
    log(f"CSVs in {OUTPUT_DIR}/ — copy with: docker cp stats-collector:{OUTPUT_DIR} ./diagnostics")


if __name__ == "__main__":
    main()
