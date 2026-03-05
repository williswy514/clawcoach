## ClawCoach Transition Table (v1)

This is a compact reference for the deterministic transition order in `HEARTBEAT.md`.

---

## Evaluation order (fixed)

1. Urgent interrupt
2. Reset mode
3. Energy change
4. Drift expiry
5. Running ↔ stuck
6. Idle ↔ running
7. Recovery/upshift
8. Trend update

---

## Transitions

| ID | From → To | Trigger (observable) | Key state updates | Regulation action | Exit |
|---|---|---|---|---|---|
| T1 | ANY → `ADJUSTING/URGENT_INTERRUPT` | `now >= event_time - prep - buffer` (from `regulation/interrupts.md`) | `mode=ADJUSTING`, `sub_state=URGENT_INTERRUPT`, `last_transition=URGENT_INTERRUPT` | override task; prep checklist; if `energy=LOW` set `success_definition=START_COUNTS` | prepared OR event start passed |
| T2 | ANY → `ADJUSTING/RESET` | `low_execution_days >= 3` | `reset_mode=true`, `sub_state=RESET`, `last_transition=ENTER_RESET` | force `granularity=0`, `time=2`, `success=START_COUNTS` | 2 startups on 2 days OR `energy=HIGH` for day |
| T3 | ANY → `ADJUSTING/LOW_ENERGY` | `ENERGY_SET(LOW)` or `state.energy=LOW` | `sub_state=LOW_ENERGY`, set low-energy guards, `last_transition=ENTER_LOW_ENERGY` | downshift (one notch) | guard: `energy>=MEDIUM` for `recovery_confirm_cycles` heartbeats |
| T4 | LOW_ENERGY → exit + `trend=RECOVERY_PHASE` | `energy>=MEDIUM` AND `startup_success_streak>=2` AND confirm cycles | `sub_state=NONE`, `mode=RUNNING|IDLE`, `trend=RECOVERY_PHASE`, `last_transition=EXIT_LOW_ENERGY` | upshift one notch | after confirm cycles satisfied |
| T5 | RUNNING → `ADJUSTING/STUCK` | no progress for `stuck_threshold_min` OR `STUCK_DECLARED` | `sub_state=STUCK`, `last_transition=ENTER_STUCK` | downshift one notch; 1 intent-check question | any `PROGRESS` or restart same task |
| T6 | IDLE → RUNNING | `START_PRESSED` OR `TASK_SELECTED` OR first `PROGRESS` | set focus fields; `startup_success_streak++`; `last_transition=STARTUP_SUCCESS` | create closure placeholder | closure |
| T7 | RUNNING → IDLE | `CLOSURE(DONE|PAUSED)` and no active focus | `mode=IDLE`, neutralize focus, `last_transition=CLOSED` | n/a | next start |
| T8 | drift lease | `DRIFT_SET(until_ts)` / `now >= drift.until_ts` | toggle `drift.allowed` and `until_ts`; set `last_transition` | gentle re-entry on expiry | on expiry |

---

## Message gating (“silence principle”)

Message only when a transition occurs:
- If `last_transition_ts == last_heartbeat_ts` → output `HEARTBEAT_OK`
- Otherwise → emit exactly one short message describing the transition

