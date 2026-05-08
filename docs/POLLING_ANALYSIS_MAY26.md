# REM Polling — Deep Analysis (May 2026)

Analysis of `app/collector.py` (969 lines), `app/benchmark_poll_cycle.py` (290 lines, Dom's measurement tool), and `app/config/config.yaml`. Written as a baseline for ongoing maintenance and tuning decisions.

---

## 1. What one cycle actually does

```
while True:                                                 # main.py:861
    control = read_collector_control()                      # JSON file
    eff = backoff.effective(control)                        # may scale settings down
    if not control["enabled"]: sleep(eff.poll_interval); continue
    do_work() → pollCloud():                                # collector.py:682
        deviceIdList = getDeviceIdList(token)               # 1 API call, returns ALL devices
        collect_power_readings(deviceIdList, ...):          # collector.py:553
            for chunk of size parallel_workers:             # ~580
                ThreadPoolExecutor: getDevPower per device  # 1 API call each, 10s timeout
                wait for all in chunk
                sleep(device_query_delay)                   # between chunks only
    record metrics, write status JSON
    sleep(poll_interval)                                    # then next cycle
```

A "round" is: `1 list call + (N_devices / parallel_workers) chunks × max(chunk_call_time) + (chunks − 1) × device_query_delay`. Then sleep `poll_interval`. Then again.

**Per-device sample spacing is `round_duration + poll_interval`, NOT `poll_interval`.** This is the single most important fact about the architecture. CHANGELOG v1.4.7 is literally a UI copy fix because it confused users repeatedly.

---

## 2. The cadence math, with realistic numbers

For `poll_interval=10s` with ~12 devices, `parallel_workers=8`:

| step | typical time |
|---|---|
| `getDeviceIdList` | ~1.0 s |
| chunk 1 (8 devices in parallel) | ~1.5–3.0 s (= max of 8 parallel calls) |
| `device_query_delay` between chunks | 0.5 s |
| chunk 2 (4 devices in parallel) | ~1.5–3.0 s |
| **total round** | **~4.5–7.5 s** |
| sleep | 10 s |
| **per-device sample spacing** | **~14.5–17.5 s** |

So with 12 devices and `poll_interval=10s`, samples land ~15s apart, not 10s. That's the floor on the design as written.

**To genuinely get 10s spacing you'd need round time ≤ 5s AND poll_interval=5s** (the floor in `_apply_poll_interval_env`, line 112). With 12 devices that means a single chunk of 12 workers.

---

## 3. Where devices "go missing" — three independent filters

There are three points at which a device disappears from a cycle:

**(a) Offline at list-time** — `collector.py:432`. If `getDeviceIdList` reports `online: false`, the device is dropped *for that entire round* before any power call is made. Online status flips on TP-Link's side based on its last cloud heartbeat. Production logs show this every cycle: `45 from API, 30 used (skipped 15 offline, 0 unsupported model)`. Some of those 15 are old plugs that should be retired; others are healthy plugs whose heartbeat just lapsed at the wrong moment.

**(b) Unsupported model** — `collector.py:436`. Hardcoded list `(P110, P110M, P115, HS110, KP115, EP10)`. Older P100s, P105 etc. have no energy meter and are silently skipped. Permanent for those models — never going to poll.

**(c) `getDevPower` returns None** — `collector.py:469`. This is the "pot luck" one. Per-device call can fail for:
- HTTP 429/503 from TP-Link (rate limit / overload, line 487)
- Rate-limit-style error message in the body (line 500)
- 10-second timeout (line 526)
- Non-200 status (line 497)
- Malformed JSON / missing `result.powerWatts` (line 510)
- Negative or non-numeric power value (line 519)

Each failure is logged and the device gets dumped into `failed_devices`, which becomes the warning line `Failed to read N device(s): X, Y, Z` and that device gets **no DB row for that timestamp**. Querying the DB later, that device looks like a hole in the timeseries — which the experimenter sees as "not polled."

**Why it feels random:** TP-Link's cloud has uneven load. On a busy second, 1–3 of 12 calls can return rate-limit messages; which 1–3 depends on which devices the TP-Link backend happens to be tail-latent for at that microsecond. Run the same experiment 5 minutes later and a different 2 devices will have holes.

---

## 4. AdaptiveBackoff (`collector.py:197–337`)

When any rate-limit signal appears in a cycle, the backoff `level` (0–8) increments. Higher levels mean:
- `poll_interval *= 2^min(level, 4)` — level 1 doubles, level 4 caps at 16×
- `parallel_workers -= (level + 1) // 2` — 1 worker dropped at level 1, 2 at level 3, 4 at level 7
- `device_query_delay += 0.25 × level`

After `COLLECTOR_BACKOFF_RECOVER_STREAK` (default 3) consecutive clean cycles, level drops by 1.

**The good:** right reflex — when TP-Link overloads, hammering harder is exactly wrong. State persists across restarts (`_load_state` reads from `collector_status.json`).

**The catch:** at base `poll_interval=10s`, ONE rate-limit hit anywhere kicks you to level 1 → effective `poll_interval=20s`. Hit at level 4+ → effective `poll_interval=160s`. So during an experiment, if TP-Link rate-limits even one device once, cadence has just doubled silently. The status file records this, but the experimenter on `/exploration` may not realise their "10s experiment" became a 20s experiment halfway through.

This is partly why "pot luck" feels worse than the raw failure rate would suggest: the failures *cause cadence to widen*, which makes the timeseries gaps more visible.

---

## 5. What scales, what doesn't

**12 devices** (today's typical):
- 2 chunks of 8 + 4. Round ~5–7s. Cycle ~15s with `poll_interval=10s`. Works.

**~30 devices** (today's full prod):
- 4 chunks of 8. Round ~8–12s. With `poll_interval=10s`, cycle ~20s. Per `POLLING_FINAL_RESULTS.md`, 20s with parallel=8 was the floor that ran reliably for 34 devices over weeks.

**100 devices** (medium-term):
- 13 chunks of 8 = round ~25–35s on best case. 8 device_query_delays = +4s. Round ~30–40s. Even with `poll_interval=5s` (minimum), per-device spacing ~35–45s. **Can't poll a 100-device fleet at 10s with this design** — maybe at 30–60s, with the understanding that rate-limit hits during peak hours could push it to 2× or worse via backoff.

**1000 devices** (ambition):
- The architecture *fundamentally won't work* with the current model: one big sequential chunk-walk through the whole fleet. With 125 chunks of 8 + 124 inter-chunk delays, the round is ~5–8 minutes minimum. Need either (a) many collectors, each polling a shard, with the TP-Link rate-limit shared across them; (b) a different polling strategy — webhook-style push from TP-Link if they offer it, or distributed polling at the device level (Tapo plugs have local LAN APIs that bypass the cloud entirely, used by `python-kasa` libraries).

The chunk-with-parallel-workers pattern *is* the right shape for ~30–100 devices. Beyond that the bottleneck isn't this code — it's the TP-Link cloud's per-account rate limit, which is **rolling-window cumulative** per CHANGELOG. No amount of compute on our end fixes that.

---

## 6. What's well-designed in Dom's code

- **The benchmark tool itself**. `benchmark_poll_cycle.py` is the right thing to have built — it measures `round_duration` directly, sweeps worker counts, computes effective cadence, and recommends settings. Data-driven design.
- **AdaptiveBackoff with persistent state**. The level survives container restarts (read from `collector_status.json` on startup, line 212). Saves rediscovering throttle points after every redeploy.
- **Settings precedence is correct**. `collector_control.json` (UI) > `POLL_INTERVAL` env > `config.yaml`. Operator changes via the UI take effect mid-run without container restart (re-read every cycle, line 863).
- **Token rotation handling** (lines 343–388 + 911). Refresh token persisted to disk; collector recovers from `-10902` "token invalid" by refreshing and retrying once.
- **Failure-counter circuit breaker**. 10 consecutive failures → exit; container restarts via Docker. Sensible.
- **Refactor for testability**. v1.5.1 extracted `collect_power_readings()` so the benchmark can call it without DB writes — a clean seam.

---

## 7. Where to point a careful eye

In rough order to address:

**(a) Failure rate is opaque to the experimenter.** When a device falls into `failed_devices`, the only evidence is a warning in collector logs. The admin UI shows current health, but during an experiment there's no "you got 28/30 samples this cycle" visible to the operator. **Fix:** surface `last_cycle_devices_polled` and `last_cycle_devices_failed` in `collector_status.json` so the UI can show a per-cycle success rate. Pure instrumentation gap.

**(b) Backoff is invisible to the experimenter.** Same theme. When `eff.poll_interval` doubles silently, the experiment is now collecting at half the configured cadence and the chart shows it but doesn't *flag* it. Effective cadence is in the status JSON; should be in the experiment export's metadata.

**(c) Round duration vs poll_interval is not enforced.** If round takes 12s and `poll_interval=5s`, you get a 12+5=17s cycle, *plus* the backoff is likely to fire because rate-limit hits cluster when pushing the API hard. The benchmark tool tells you this AFTER you ask; the collector itself never says "your settings imply ~17s effective; refuse settings that imply <X s?". Could be a Lab-tier "advanced settings validation" that warns at save time.

**(d) The 10s `getDevPower` timeout (line 477) interacts badly with parallel chunks.** A single slow device holds up the entire chunk because the chunk waits for `as_completed`. With 8 in flight and 1 timing out, chunk becomes 10s regardless of how fast the other 7 were. **Fix candidate:** lower per-call timeout to 4–5s and accept the failed reading.

**(e) Rate-limit signal scope is too coarse.** A rate-limit on one device taints the whole cycle (`note_rate_limit()` increments a global counter, `record_cycle` checks "any > 0"). One throttled device escalates backoff for the entire fleet. Trade-off is sensitivity vs noise. Could track rate-limit hits as a *fraction* of device calls and only escalate when fraction > threshold.

**(f) "Offline" filtering at list-time hides flap.** A plug that flaps online/offline over a 5-minute window appears as scattered missing rows in the DB, indistinguishable from a `getDevPower` failure. Recording the "offline-at-list-time" set in the status JSON would let you tell the difference between "the plug is unhealthy" vs "TP-Link is rate-limiting us."

**(g) `parallel_workers=8` may not be optimal for the current fleet.** Dom's `--sweep` benchmark exists exactly to find this. For ~12 devices a single chunk of 12 workers may beat 2 chunks of 8 — round time becomes `1× max(parallel_call_time)` instead of `2× max(...) + delay`.

**(h) The DB write is in the cycle's critical path** (in the same thread). With a hypertable and modest writes (12 rows per cycle), this isn't a real problem now, but at 1000 devices it would be. Fix is straightforward: queue points to a writer thread.

---

## 8. The "10s and devices missing" symptom — most likely combination

In order of probability:

1. **`getDevPower` is failing for a small rotating subset of devices** — TP-Link cloud overload. Pot luck. Confirm by tailing collector logs during an experiment: look for `Failed to read N device(s): X, Y, Z`.
2. **AdaptiveBackoff has silently kicked in** during the experiment — `eff.poll_interval` is no longer 10s. Confirm via `cat /app/data/admin/collector_status.json` while the experiment runs; check `effective.poll_interval` vs `configured.poll_interval`.
3. **A subset of selected devices were `online: false` at list-time** — heartbeat flap. Check `skipped N offline` in the cycle log and which devices were in that group.
4. **Round time exceeds 10s structurally** — even before any failure, cycle is `round + 10s`, not 10s. With 12 devices ~15s; perceived as 10s but appearing as 15s spacing in the chart.

**Cheapest diagnostic:** start an experiment with `LOG_LEVEL=DEBUG` and tail `docker logs -f stats-collector` while it runs. Every cycle prints round time, device count, and failure list.

---

## 9. Recommended ordering of changes

**Before changing any code:**
1. Run `docker compose exec collector python /app/benchmark_poll_cycle.py --sweep --rounds 5` in typical fleet shape to find the worker count that minimises round time.
2. Audit the `online: false` devices once — identify the genuine retired plugs vs the flapping-but-healthy ones.

**Small, high-value changes:**
3. Surface per-cycle success rate in `collector_status.json` and on the admin UI during experiments.
4. Lower per-call `getDevPower` timeout from 10s to 4–5s.
5. Make AdaptiveBackoff trigger on *fraction* of devices throttled, not absolute count.

**Structural changes (only if committing to scaling):**
6. For >100 devices, split into shards each with their own collector, sharing TP-Link rate budget via a coordinator. Or evaluate `python-kasa` for LAN-direct polling that bypasses the cloud entirely.
7. Move DB writes to a worker thread.

**Don't touch:** AdaptiveBackoff's existence (right reflex), `benchmark_poll_cycle.py` (genuinely useful), settings-precedence chain (sensible), token persistence (clean).
