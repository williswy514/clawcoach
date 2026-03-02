# ClawCoach Heartbeat Loop

Every cycle:

1. Load state.json
2. Load energy_log.json
3. Load queue.md
4. Load interrupts.md
5. Load drift.md
6. Load routine.md

---

Step 1: Check urgent interrupt

If current_time >= event_time - prep - buffer:
  mode = URGENT_INTERRUPT
  Trigger preparation steps
  STOP

---

Step 2: Check reset mode

If low_execution_days >= 3:
  reset_mode = true
  Only allow 2-minute tasks
  No productivity language

---

Step 3: Energy regulation

If energy == LOW:
  Downshift:
    Granularity → smaller
    Time expectation → shorter
    Success = START_COUNTS

If energy >= MEDIUM AND startup_success_streak >= 2:
  Upshift granularity one level

---

Step 4: Choose task

Score tasks.
If Important & Urgent:
  Lock main track.
Else if drift allowed:
  Permit side.
Else:
  Choose highest score main track.

---

Step 5: Inactivity check

If no startup logged:
  Propose smallest viable start (2–5 min).

---

Step 6: Closure check

If task started but not closed:
  Ask for:
    Done / Paused / Next tiny step

---

If no condition triggered:
  HEARTBEAT_OK