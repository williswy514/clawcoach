# ClawCoach Heartbeat Engine

On every heartbeat:

---------------------------------------
STEP 0 — Load Core Files
---------------------------------------

Load:
- state/state.json
- state/events.jsonl (if exists)
- regulation/queue.md
- regulation/interrupts.md
- regulation/drift.md
- routine/routine.md

Set NOW = current time


---------------------------------------
STEP 1 — Apply New Events
---------------------------------------

For each new event since last_heartbeat_ts:

If ENERGY_SET:
  state.energy = value

If START_PRESSED:
  set mode transition candidate STARTUP

If PROGRESS:
  update current_focus.last_progress_ts = NOW

If CLOSURE:
  mark task closed
  clear current_focus

If DRIFT_SET:
  state.drift.allowed = true
  state.drift.until_ts = provided time


---------------------------------------
STEP 2 — Transition Evaluation Order
---------------------------------------

Evaluate in strict order:

1) URGENT INTERRUPT

If NOW >= event_time - prep - buffer:
  mode = ADJUSTING
  sub_state = URGENT_INTERRUPT
  last_transition = URGENT_INTERRUPT
  GOTO REGULATION


2) RESET MODE

If low_execution_days >= 3:
  reset_mode = true
  mode = ADJUSTING
  sub_state = RESET
  last_transition = ENTER_RESET
  GOTO REGULATION


3) ENERGY TRANSITION

If energy == LOW AND sub_state != LOW_ENERGY:
  mode = ADJUSTING
  sub_state = LOW_ENERGY
  last_transition = ENTER_LOW_ENERGY
  GOTO REGULATION

If energy >= MEDIUM AND sub_state == LOW_ENERGY:
  increase recovery_candidate_cycles
  If recovery_candidate_cycles >= 2:
    sub_state = NONE
    mode = RUNNING or IDLE
    last_transition = EXIT_LOW_ENERGY
    GOTO REGULATION


4) DRIFT EXPIRY

If drift.allowed == true AND NOW >= drift.until_ts:
  drift.allowed = false
  last_transition = DRIFT_EXPIRED
  GOTO REGULATION


5) STUCK DETECTION

If mode == RUNNING AND
   NOW - current_focus.last_progress_ts >= 15 minutes:
    mode = ADJUSTING
    sub_state = STUCK
    last_transition = ENTER_STUCK
    GOTO REGULATION


6) STARTUP

If START_PRESSED event detected:
  mode = RUNNING
  sub_state = NONE
  startup_success_streak += 1
  last_transition = STARTUP_SUCCESS
  GOTO REGULATION


---------------------------------------
STEP 3 — Regulation Adjustments
---------------------------------------

If entering LOW_ENERGY or STUCK:
  Downshift:
    granularity_level - 1 (min 0)
    time_expectation shorter
    success_definition = START_COUNTS

If exiting LOW_ENERGY:
  Upshift one level only


---------------------------------------
STEP 4 — Task Selection
---------------------------------------

If no active focus:
  Score tasks from queue.md
  If important+urgent:
    select main track
  Else if drift allowed:
    allow side
  Else:
    select highest score


---------------------------------------
STEP 5 — Closure Check
---------------------------------------

If task started but no closure logged:
  ask for:
    Done / Paused / Next tiny step


---------------------------------------
STEP 6 — Silence Principle
---------------------------------------

If last_transition updated this cycle:
  Output minimal regulation message

Else:
  Output: HEARTBEAT_OK


---------------------------------------
STEP 7 — Save State
---------------------------------------

Update:
- last_transition_ts
- last_heartbeat_ts
Write state/state.json

End.