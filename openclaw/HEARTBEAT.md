# ClawCoach Heartbeat — Task Regulation Engine (Local-first)

On every heartbeat:

Load:
- state/state.json
- regulation/queue.json

Set NOW = current time
Let EVENT_TEXT = triggering system event text (or empty)
Let PREV_ENERGY = state.energy
Let PREV_MODE = state.mode
Let PREV_SUB_STATE = state.sub_state
Let PREV_GRANULARITY = state.dials.granularity
Let PREV_TIME_BOX = state.dials.time_box_min
Let INPUT_SIGNAL_DETECTED = false

----------------------------------------
1) Parse command signals from EVENT_TEXT
----------------------------------------

If EVENT_TEXT contains "ENERGY_SET LOW":
  set INPUT_SIGNAL_DETECTED = true
  set state.energy = LOW
If EVENT_TEXT contains "ENERGY_SET MEDIUM":
  set INPUT_SIGNAL_DETECTED = true
  set state.energy = MEDIUM
If EVENT_TEXT contains "ENERGY_SET HIGH":
  set INPUT_SIGNAL_DETECTED = true
  set state.energy = HIGH

If EVENT_TEXT (case-insensitive) contains any of:
- "not good"
- "not feeling good"
- "low energy"
- "tired"
- "exhausted"
- "overwhelmed"
- "can't start"
- "cannot start"
- "hard to start"
- "not okay"
- "feeling bad"
- "drained"
- "burned out"
- "burnt out"
- "stuck"
- "no motivation"
- "procrastinating"
- "can't focus"
- "cannot focus"
- "brain fog"
Then:
  set INPUT_SIGNAL_DETECTED = true
  set state.energy = LOW
  if desired_start_minutes does not exist: set desired_start_minutes = 2
  set state.last_transition = "AUTO_LOW_ENERGY_DETECTED"

If EVENT_TEXT contains "START 2":  set desired_start_minutes = 2
If EVENT_TEXT contains "START 10": set desired_start_minutes = 10
If EVENT_TEXT contains "START 25": set desired_start_minutes = 25
If EVENT_TEXT contains "START ": set INPUT_SIGNAL_DETECTED = true

If EVENT_TEXT contains "DRIFT 10":
  set INPUT_SIGNAL_DETECTED = true
  set drift_minutes = 10
If EVENT_TEXT contains "DRIFT 30":
  set INPUT_SIGNAL_DETECTED = true
  set drift_minutes = 30
If EVENT_TEXT contains "DRIFT 60":
  set INPUT_SIGNAL_DETECTED = true
  set drift_minutes = 60

If EVENT_TEXT contains "PROGRESS":
  set INPUT_SIGNAL_DETECTED = true
  set state.current_focus.last_progress_ts = NOW
  set state.next_nudge_ts = NOW + 15 minutes
  set state.last_transition = "PROGRESS_PING"

If EVENT_TEXT contains "CLOSURE DONE":
  set INPUT_SIGNAL_DETECTED = true
  clear current_focus
  set state.mode = IDLE
  set state.sub_state = NONE
  set state.next_nudge_ts = null
  set state.time_box_ends_at = null
  set state.last_transition = "CLOSED_DONE"

If EVENT_TEXT contains "CLOSURE PAUSED":
  set INPUT_SIGNAL_DETECTED = true
  clear current_focus
  set state.mode = IDLE
  set state.sub_state = NONE
  set state.next_nudge_ts = null
  set state.time_box_ends_at = null
  set state.last_transition = "CLOSED_PAUSED"

----------------------------------------
2) Dials from energy (downshift/upshift)
----------------------------------------

If state.energy == LOW:
  state.mode = "ADJUSTING"
  state.sub_state = "LOW_ENERGY"
  state.dials.granularity = "FAKE_START"
  state.dials.time_box_min = 10
  state.dials.success_definition = "START_COUNTS"
  set state.last_transition = "ENTER_LOW_ENERGY"

If state.energy == MEDIUM:
  if state.sub_state == "LOW_ENERGY":
    state.sub_state = "NONE"
    state.mode = "RUNNING" if state.current_focus.task_id != null else "IDLE"
    set state.last_transition = "EXIT_LOW_ENERGY"
  if state.dials.granularity == "FAKE_START": state.dials.granularity = "TINY"
  if state.dials.time_box_min < 25: state.dials.time_box_min = 25
  state.dials.success_definition = "STAGE"

If state.energy == HIGH:
  if state.dials.granularity != "SMALL": state.dials.granularity = "SMALL"
  state.dials.time_box_min = 30
  state.dials.success_definition = "STAGE"

----------------------------------------
3) Start command enters RUNNING
----------------------------------------

If desired_start_minutes exists:
  state.mode = "RUNNING"
  state.sub_state = "NONE" if state.energy != LOW else "LOW_ENERGY"
  state.dials.time_box_min = desired_start_minutes
  if state.current_focus.task_id is null:
    set state.next_nudge_ts = NOW
  set state.time_box_ends_at = NOW + desired_start_minutes minutes
  set state.last_transition = "START_REQUESTED"

----------------------------------------
4) Choose task and generate next action
----------------------------------------

If state.mode != "IDLE" AND state.current_focus.task_id is null:

  For each task:
    score = 0.45*urgency + 0.45*importance + 0.10*activation_cost

  Choose highest score task (prefer track=main)

  state.current_focus.task_id = chosen.id
  state.current_focus.started_ts = NOW
  state.current_focus.last_progress_ts = NOW
  state.current_focus.next_action_text = chosen.next_actions[state.dials.granularity]

  state.next_nudge_ts = NOW + state.dials.time_box_min minutes
  set state.time_box_ends_at = NOW + state.dials.time_box_min minutes
  set state.last_transition = "TASK_SELECTED"

----------------------------------------
5) Nudge loop (task-based)
----------------------------------------

If state.next_nudge_ts != null AND NOW >= state.next_nudge_ts AND state.current_focus.task_id != null:

  Output one nudge:
  "Now: {state.dials.time_box_min} minutes. Next: {state.current_focus.next_action_text}"

  state.next_nudge_ts = NOW + state.dials.time_box_min minutes
  set state.time_box_ends_at = NOW + state.dials.time_box_min minutes
  set state.last_transition = "NUDGE_SENT"

If state.energy == LOW AND state.current_focus.task_id is null:
  If state.next_nudge_ts == null OR NOW >= state.next_nudge_ts:
    Output one regulation nudge:
    "You don't need to feel ready. Let's do a {state.dials.time_box_min}-minute start: open the task list and pick one tiny first move."
    state.next_nudge_ts = NOW + state.dials.time_box_min minutes
    set state.time_box_ends_at = NOW + state.dials.time_box_min minutes
    set state.last_transition = "LOW_ENERGY_START_NUDGE"

----------------------------------------
5b) Timer display and reminder (aligned to current step)
----------------------------------------

When outputting to the user and state.time_box_ends_at is set (any energy level):
  Always append (or show separately) so the user sees both:
  - "Timer: {state.dials.time_box_min} min — ends at {state.time_box_ends_at}."
  - "I'll remind you when this step is up."
Timer and reminder are aligned to the current step length (state.dials.time_box_min). The client/UI should display the timer and trigger the next heartbeat at state.next_nudge_ts (= time_box_ends_at) so the reminder is sent when the current step ends.

----------------------------------------
6) Save + Silence Principle
----------------------------------------

Write state/state.json with last_heartbeat_ts = NOW

Let STATE_CHANGED_FROM_INPUT =
  EVENT_TEXT is not empty AND (
    PREV_ENERGY != state.energy OR
    PREV_MODE != state.mode OR
    PREV_SUB_STATE != state.sub_state OR
    PREV_GRANULARITY != state.dials.granularity OR
    PREV_TIME_BOX != state.dials.time_box_min
  )

If INPUT_SIGNAL_DETECTED == true AND STATE_CHANGED_FROM_INPUT:
  Output:
  "Updated from your input: energy {PREV_ENERGY}->{state.energy}, mode {PREV_MODE}->{state.mode}, focus size {PREV_GRANULARITY}->{state.dials.granularity}, timer {PREV_TIME_BOX}->{state.dials.time_box_min}m."
  If state.time_box_ends_at is set:
    Also output: "Timer: {state.dials.time_box_min} min — ends at {state.time_box_ends_at}. I'll remind you when this step is up."
Else if last_transition changed this cycle:
  If state.current_focus.task_id != null:
    Output:
    "State: {state.energy}/{state.dials.granularity}. Next: {state.current_focus.next_action_text}"
  Else:
    Output:
    "State: {state.energy}/{state.dials.granularity}. Next: take one tiny starter action."
  If state.time_box_ends_at is set:
    Also output: "Timer: {state.dials.time_box_min} min — ends at {state.time_box_ends_at}. I'll remind you when this step is up."
Else:
  If state.energy == LOW:
    Output: "State: LOW. Start counts. Reply PROGRESS after any tiny move."
    If state.time_box_ends_at is set:
      Also output: "Timer: {state.dials.time_box_min} min — ends at {state.time_box_ends_at}. I'll remind you when this step is up."
  Else:
    Output: HEARTBEAT_OK