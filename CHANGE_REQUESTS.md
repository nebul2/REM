# REM — Change Requests

> Active change requests for REM, Keep-a-Changelog-style. Closed CRs move to
> `CHANGE_REQUESTS_CLOSED.md` when shipped (file created on first close).
>
> Format: each CR has a number, title, status, problem, direction, and rough
> scope estimate. Status values: **Open** (in queue), **In progress**, **Deferred**,
> **Blocked**, **Closed** (moved to closed file with shipping commit).

---

## CR-001 — Mid-tier focus mode (interleaved cadence)

**Status:** Deferred (captured 2026-05-08)

**Problem:** Today's `focus_level` toggle is binary: Off (everyone polled at the
same ambient `poll_interval`) or Strong (only experiment devices polled, all
others paused). Strong is the right choice for mission-critical experiments
where cadence precision is everything, but it sacrifices ambient observability
of the rest of the fleet for the duration. There's a useful middle ground: keep
ambient polling active at a slower rate (continuous fleet history) while the
experiment subset gets the tight cadence it needs.

**Direction:** Add a third level — **Mid** — between Off and Strong. Two
interleaved tick rates running inside the same collector loop:

```
focus tick     = experiment.target_cadence_s   (e.g. 10s) — experiment devices
ambient tick   = collector_control.poll_interval (e.g. 30s) — everyone else
```

Sketch:
- Focus tick is the heartbeat. Every Nth focus tick (where N = ambient/focus
  ratio) also polls the ambient devices in the same cycle.
- Slip-recovery (already implemented) catches combined cycles that overrun and
  re-anchors to the next focus tick — operator sees yellow→orange health pill
  and can ratchet up to Strong if it doesn't recover.
- The TP-Link rate-limit budget needs explicit accounting: focus calls/min +
  ambient calls/min + 2 list calls/min. For typical fleets (12 focus + 22
  ambient) this is ~72 calls/min, well within the proven floor of ~105/min
  (POLLING_FINAL_RESULTS.md).

**Scope:** ~2–3 hours of careful work. Single-threaded interleaved scheduler.
Test cases include:
- Ambient round duration > (focus_tick − focus_round) headroom
- Adaptive backoff firing globally vs per-tier (today it's global; for Mid we
  may want to scope it)
- Focus experiment ending mid-cycle while ambient phase is in progress

**Why deferred:** Strong already covers the mission-critical case with provable
cadence. Mid is a nice-to-have for "I want continuous fleet history during my
experiment" — capture when an operator actually asks for it, rather than
building speculatively.

**Open architectural call inside Mid:**
- Interleaved ticks (single-threaded) vs separate ambient thread sharing the
  TP-Link token. Start with interleaved; only go threaded if precision in
  practice falls below requirement.

**Related:** the original "Background Polling" concept Ben floated (memory
file `rem_background_polling_concept.md`) is the same shape from a different
angle — Mid is what background polling becomes once it's defined relative to
an active focus experiment.

---

## CR-002 — Auto-calibrated focus health thresholds

**Status:** Deferred (captured 2026-05-08)

**Problem:** Today's health pill thresholds are a fixed % of tick — green ≤30%,
yellow 30–70%, orange 70–95%, red >95%. Robust and debuggable, but the same
yardstick for every fleet shape. A focus experiment whose steady-state
sits at 45% (e.g. 12 devices @ 10s tick) will always show yellow, even though
the cadence is perfectly stable for *that* fleet+account combination. The
operator can't distinguish "healthy stable yellow" from "drifting toward
trouble yellow."

**Direction:** When an experiment starts in Focus mode, run a short pre-flight
benchmark over its devices using the existing `app/benchmark_poll_cycle.py`
tool (~5 seconds wall time). Capture mean μ and standard deviation σ of round
time. Calibrate thresholds to that fleet:

```
green   round_time < μ + 1σ                         (within normal jitter)
yellow  μ + 1σ ≤ round_time < μ + 3σ                (slower than usual but recoverable)
orange  round_time > μ + 3σ  OR  > 0.85 × tick      (anomalous + tick-pressure)
red     round_time > 0.95 × tick                    (slip imminent)
```

This way the pill says "you're outside the established baseline" rather than
"you're outside an arbitrary fixed-% bucket." Adapts naturally to fleets that
run hot vs cool, accounts that respond fast vs slow.

**Scope:** ~3–4 hours.
- Pre-flight benchmark trigger on `start_experiment` when `focus_level=2` and
  device_count ≥ 2 (skip for single-device experiments).
- Store calibrated `{round_mean_s, round_std_s, calibrated_at}` on the
  experiment record.
- `_compute_health()` reads calibrated values when present; falls back to the
  current fixed-% logic when not.
- UI: indicate calibrated vs uncalibrated state on the health pill tooltip.

**Why deferred:** the current fixed-% thresholds are working — operators can
read "27% used, green" at a glance and the meaning is clear. Calibrated
thresholds add steps (pre-flight wait, store/restore, recalibration on fleet
changes) for a more nuanced signal that may or may not actually help. Worth
shipping when an operator complains "the pill goes yellow when nothing's
wrong" or "the pill stays green right up to the moment of slip."

**Related:** depends on `app/benchmark_poll_cycle.py` (already exists — Dom's
work). Touches `_compute_health()` in `app/collector.py` and the start-flow
endpoint in `admin/app.py`.

---

## CR-003 — Code hygiene: credentials, logging, and app.py decomposition

**Status:** Open (captured 2026-06-29)

**Problem:** Three concrete issues surfaced in a code review that will compound
if left unaddressed:

1. **Hardcoded TP-Link OAuth client credentials** (`collector.py:383`). The
   `client_id` and `client_secret` for the TP-Link token-refresh call are
   literals in source. `ENV_TEMPLATE` already defines `TPLINK_CLIENT_ID` and
   `TPLINK_CLIENT_SECRET` — they were never wired up. Low exploit risk today
   (these are developer-platform app credentials, not account credentials), but
   they'll rotate eventually and require a redeploy to change.

2. **`load_groups()` logs to stdout instead of the logger** (`admin/app.py:203`).
   The error path does `print(f"Error loading groups: {e}")` — invisible in
   structured logs. The silent-return-`{}` fallback is fine for a non-critical
   config file, but the error needs to reach the log aggregator.

3. **`admin/app.py` is 2,552 lines** — routes, business logic, and data-loading
   in one file. Navigability and testability degrade as it grows. No hard
   deadline, but the split should happen before the file needs another major
   feature.

**Direction:**

**(1) Wire credentials from env vars** — `collector.py:383`, change the literal
dict to read `os.getenv("TPLINK_CLIENT_ID")` and `os.getenv("TPLINK_CLIENT_SECRET")`.
Raise clearly if either is missing at startup rather than letting a malformed
token request propagate downstream.

**(2) Replace `print()` with `logger.error()`** — sweep `admin/app.py` for any
remaining `print()` calls in exception handlers and convert to the module logger.
Keep the `return {}` fallback in `load_groups()`; just make the error visible.

**(3) Begin decomposing `admin/app.py`** along natural seams:
- `admin/services/groups.py` — `load_groups()`, `save_groups()`, group CRUD logic
- `admin/services/registry.py` — device registry reads/writes (thin wrappers
  over `device_registry.py` that already exists)
- `admin/routes/` — Flask Blueprint per domain (devices, experiments, analytics,
  focus)
- `admin/app.py` — drops to app factory + Blueprint registration only

**Scope:**
- Items 1 and 2: ~1 hour combined. Straightforward, high confidence.
- Item 3: ~4–6 hours. Low risk per module (move code, fix imports, verify
  Flask routing still resolves). Can be done incrementally — one Blueprint per
  session — without touching unrelated logic.

**Why not deferred:** Items 1 and 2 are small and strictly better. Item 3 is
the kind of work that only gets harder the longer it waits; the next feature
landed in `app.py` adds another 100–200 lines.

---

## CR-004 — Field devices unknown to REM (LEM brings its own devices)

**Status:** Open (captured 2026-07-23)

**Problem / motivation:** A core purpose of LEM is to reduce dependence on the
TP-Link cloud. Today, a plug only reaches REM if it was shared to the GoS Tapo
account and the cloud collector discovers it. We want a volunteer who joins with
LEM to be able to contribute measurements for **devices REM was never aware of**
— a Tapo plug not on the GoS account, a Shelly (LEM already abstracts device
types), or any future LEM-supported meter. This makes LEM a genuine alternative
data path, not just a denser mirror of cloud-known devices.

**Current state:** The field API (`admin/field_api.py`) already inserts field
rows under whatever alias LEM sends and auto-adds that alias to a
`field-<experiment>` group linked to the experiment (`_ensure_field_group`). So
an unknown alias *does* land in `gos_rem` and *is* associated with the
experiment for export. **The gap is the live view:** the exploration/live-plot
logic and the device registry are built around devices the collector knows
(groups → registry → plot). A brand-new field alias won't appear on the live
experiment chart dynamically, and isn't a first-class citizen anywhere in the UI.

**Direction (both sides need work):**
- **REM:** treat field-contributed aliases as first-class in the live experiment
  view — dynamically add a new device to the live plot as its first rows arrive,
  without a manual group/registry step. Likely a "field/ad-hoc device" concept
  distinct from cloud-registry devices, surfaced in the exploration UI and device
  lists. Review how `resolve_experiment_devices_and_time_range` + the exploration
  JS build the device set so newly-arrived field aliases are included live.
- **LEM:** already sends the device's identity (Tapo nickname today); for
  non-Tapo devices, define the identity/label it reports so REM can namespace it
  and avoid collisions with cloud aliases.

**Open questions (for Ben):**
1. Device scope: just Tapo plugs not on the GoS account, or genuinely other
   hardware (Shelly, etc.) too?
2. Should ad-hoc field devices **persist** in REM's device registry, or be
   **experiment-scoped / ephemeral**?
3. Identity/namespacing: how to avoid a field device's name colliding with a
   cloud device's alias? A `field:` prefix, or trust operator-set names?
4. Live plot: auto-add new field devices to the chart, or require an operator
   "accept" (guards against a rogue LEM spamming devices — ties to the planned
   field rate-limiting / stress-test work)?

**Scope:** Non-trivial — touches field_api, the device/registry model, and the
exploration live-plot JS. Estimate after the open questions are settled.

**Related:** builds on the field ingest API (CR-shipped 2026-07-23); the rogue-
LEM concern overlaps the planned REM stress-test / rate-limiting work.
