## ClawCoach State Schema (v1)

Single source of truth: `state/state.json`
Optional signals log: `state/events.jsonl` (append-only JSONL)

This document is a human-readable spec for the state + transition system implemented by `HEARTBEAT.md`.

---

## Files

- `state/state.json`: authoritative state snapshot (read/write each heartbeat)
- `state/events.jsonl`: optional append-only stream of observable signals (recommended)
- `state/energy_log.json`: optional historical log (must be valid JSON; recommended format: array)
- `state/metrics.json`: optional aggregates and counters

---

## `state/state.json` fields

### Versioning
- `version` (number): schema version (currently `1`)

### Primary state
- `mode`: `IDLE | RUNNING | ADJUSTING`
- `sub_state`: `NONE | LOW_ENERGY | STUCK | RESISTANCE | URGENT_INTERRUPT | RESET`
- `trend`: `STABLE_WEEK | DRIFTING_WEEK | LOW_ENERGY_PHASE | RECOVERY_PHASE`

### Energy
- `energy`: `LOW | MEDIUM | HIGH`
- `energy_confidence`: `SELF_REPORT` (extend later if needed)

### Current focus
`current_focus`:
- `task_id` (string|null)
- `track` (string|null)
- `granularity_level` (number): `0..3` where `0=FAKE_START`, `1=TINY`, `2=SMALL`, `3=NORMAL`
- `time_expectation_min` (number): expected minutes for the current step
- `mode_switch`: `WRITE | OUTLINE | TITLE | VOICE_DRAFT | NONE`
- `success_definition`: `FINISH | STAGE | START_COUNTS | NONE`
- `started_ts` (ISO string|null)
- `last_progress_ts` (ISO string|null)

### Counters / flags
- `startup_success_streak` (number)
- `last_startup_ts` (ISO string|null)
- `low_execution_days` (number)
- `reset_mode` (boolean)

### Drift lease
`drift`:
- `allowed` (boolean)
- `until_ts` (ISO string|null)

### Guards (anti-oscillation)
`guards`:
- `min_cycles_in_low_energy` (number)
- `low_energy_enter_cycle` (number|null)
- `recovery_confirm_cycles` (number)
- `recovery_candidate_cycles` (number)

### Heartbeat bookkeeping (for silence gating)
- `last_transition` (string|null)
- `last_transition_ts` (ISO string|null)
- `last_heartbeat_ts` (ISO string|null)

---

## `state/events.jsonl` format

Each line is a JSON object with at least:
- `ts` (ISO string)
- `type` (string)

Recommended event shapes:

```json
{"ts":"2026-03-02T10:00:00Z","type":"ENERGY_SET","value":"LOW"}
{"ts":"2026-03-02T10:03:00Z","type":"START_PRESSED","minutes":2}
{"ts":"2026-03-02T10:06:00Z","type":"PROGRESS","task_id":"thesis-01"}
{"ts":"2026-03-02T10:25:00Z","type":"CLOSURE","result":"PAUSED","next_step":"open doc"}
```

If you don’t use `events.jsonl`, you can still operate by editing `state.json` directly, but transitions become less reliable.

---

## Defaults / thresholds

- `stuck_threshold_min`: 15
- `inactivity_threshold_min`: 90 (quiet default)
- `recovery_confirm_cycles`: 2 heartbeats
- Reset trigger: `low_execution_days >= 3`

