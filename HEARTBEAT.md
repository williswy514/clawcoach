# ClawCoach Heartbeat (Chat-Inference Version)

On every heartbeat:

----------------------------------------
STEP 0 — Load
----------------------------------------
Load:
- state/state.json
- regulation/queue.md

Set NOW = current time

Assume the heartbeat has access to the most recent user message in this session.
Call it: LAST_USER_MESSAGE

----------------------------------------
STEP 1 — Convert chat text into signals (NO manual trigger)
----------------------------------------

# 1) Energy inference (deterministic pattern match)
If LAST_USER_MESSAGE contains any of:
- "i'm down"
- "im down"
- "low energy"
- "tired"
- "exhausted"
- "no energy"
- "can't start"
- "cannot start"
- "overwhelmed"
- "burnt out"

Then set:
  state.energy = LOW
  state.last_transition = "CHAT_ENERGY_LOW"

Else if LAST_USER_MESSAGE contains any of:
- "i feel ok"
- "medium energy"
- "better now"
- "back to normal"

Then set:
  state.energy = MEDIUM
  state.last_transition = "CHAT_ENERGY_MEDIUM"

Else if LAST_USER_MESSAGE contains any of:
- "high energy"
- "i feel great"
- "let's go"
- "i can focus"

Then set:
  state.energy = HIGH
  state.last_transition = "CHAT_ENERGY_HIGH"

# 2) Explicit time preference from chat (optional)
If LAST_USER_MESSAGE contains "30 min" or "30 minutes":
  state.current_focus.time_expectation_min = 30

If LAST_USER_MESSAGE contains "10 min" or "10 minutes":
  state.current_focus.time_expectation_min = 10

If LAST_USER_MESSAGE contains "5 min" or "5 minutes":
  state.current_focus.time_expectation_min = 5

----------------------------------------
STEP 2 — Transitions
----------------------------------------

# Enter LOW_ENERGY
If state.energy == LOW AND state.sub_state != "LOW_ENERGY":

  state.mode = "ADJUSTING"
  state.sub_state = "LOW_ENERGY"
  state.last_transition = "ENTER_LOW_ENERGY"

  # Ensure baseline
  If state.current_focus.time_expectation_min == 0:
    state.current_focus.time_expectation_min = 30

  # Downshift time expectation explicitly to 10 (your goal)
  If state.current_focus.time_expectation_min >= 30:
    state.current_focus.time_expectation_min = 10
  Else if state.current_focus.time_expectation_min > 10:
    state.current_focus.time_expectation_min = 5
  Else:
    state.current_focus.time_expectation_min = 2

  state.current_focus.success_definition = "START_COUNTS"

  # Select a task if none
  If state.current_focus.task_id is null:
    Select highest-score main-track task from regulation/queue.md
    state.current_focus.task_id = selected task id
    state.current_focus.started_ts = NOW
    state.current_focus.last_progress_ts = NOW

  # Schedule nudge in 10 minutes
  state.next_nudge_ts = NOW + 10 minutes

  GOTO SAVE_AND_OUTPUT


# Exit LOW_ENERGY (simple version)
If state.energy != LOW AND state.sub_state == "LOW_ENERGY":
  state.sub_state = "NONE"
  state.mode = "RUNNING" if state.current_focus.task_id != null else "IDLE"
  state.last_transition = "EXIT_LOW_ENERGY"
  GOTO SAVE_AND_OUTPUT


----------------------------------------
STEP 3 — Nudge loop (reminder)
----------------------------------------

If state.next_nudge_ts != null AND NOW >= state.next_nudge_ts:

  If state.sub_state == "LOW_ENERGY":
    Output exactly one nudge:
      "Low energy mode. 2 minutes: just open the file / doc for {task_id}."
    state.next_nudge_ts = NOW + 10 minutes
    GOTO SAVE_AND_OUTPUT

  Else:
    state.next_nudge_ts = null
    GOTO SAVE_AND_OUTPUT


----------------------------------------
STEP 4 — Silence principle output
----------------------------------------

SAVE_AND_OUTPUT:

Write updated state/state.json (including timestamps)

If state.last_transition changed this cycle:
  Output a single short message:
    "State updated: {sub_state}. Time now {time_expectation_min} minutes. Success = START."
Else:
  Output: HEARTBEAT_OK
