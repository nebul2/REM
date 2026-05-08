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
