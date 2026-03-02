## ClawCoach

ClawCoach is **not** a task manager.

It is a **behavior regulation layer** that sits between your intentions and your actions. It keeps your direction stable while letting your execution flex with your energy, context, and interruptions.

Core principle: **保持方向，改变方式** — keep the direction, change the method.

Silence is a feature: if nothing important is changing, ClawCoach stays out of the way.

---

## OpenClaw Layout

This repo follows the **OpenClaw** layout: everything lives in a few high‑signal folders that mirror how your day actually runs.

- **Root files**
  - `SOUL.md` — Why ClawCoach exists for you. Core philosophy and identity.
  - `RULES.md` — System rules and guardrails (silence, energy regulation, drift, no shame).
  - `TOOLS.md` — What the system is allowed to do (read/write files, no external APIs by default).
  - `HEARTBEAT.md` — The heartbeat loop: how each cycle reads state, checks interrupts, regulates energy, and decides whether to speak or stay silent.

- **state/**
  - `state.json` — Current machine state: mode flags, streaks, last task, etc.
  - `events.jsonl` — Optional append-only signal log (JSONL) used for deterministic transitions.
  - `energy_log.json` — Log of energy samples over time (LOW / MEDIUM / HIGH, plus metadata).
  - `metrics.json` — Aggregate metrics (streaks, low‑execution days, resets entered, etc.).

- **direction/**
  - `goals.md` — Long‑term and medium‑term goals. Direction is **stable**; do not rewrite this based on mood.
  - `projects.md` — Active projects that realize those goals.
  - `priorities.md` — Current priorities / focus ordering across projects.

- **regulation/**
  - `queue.md` — Task queue and main track items, with scores (importance, urgency, energy fit).
  - `focus_block.md` — The current or next focus block (time window, constraints, buffer).
  - `interrupts.md` — Upcoming time‑bound events that can trigger urgent mode.
  - `drift.md` — Controlled “drift” / side‑quests with return conditions.
  - `closure.md` — Open loops that need explicit closure decisions (Done / Paused / Next tiny step).

- **routine/**
  - `routine.md` — Baseline daily / weekly routines; how a normal day looks.
  - `sleep_guard.md` — Sleep boundary rules and constraints so productivity never eats sleep.

- **memory/**
  - `MEMORY.md` — How memory works: what gets logged, how to review it.
  - `daily/YYYY-MM-DD.md` — Daily memory page (e.g. `daily/2026-03-02.md`) with logs, reflections, and state snapshots.

---

## How the Heartbeat Works

Each **heartbeat cycle** (manual or automated) runs the loop defined in `HEARTBEAT.md`:

1. Load core state (`state/state.json`) and regulation inputs (`regulation/*`, `routine/*`).
2. Read new signals from `state/events.jsonl` (optional but recommended).
3. Evaluate transitions in a strict order (urgent interrupt → reset → energy → drift → stuck/running → idle/running → recovery → trend).
4. Apply regulation dials (downshift/upshift) only when entering/exiting adjustment states.
5. Write updated `state/state.json`.
6. Message only on transitions; otherwise: `HEARTBEAT_OK`.

The system **never shames, moralizes, or enters therapy mode**. It mirrors behavior and suggests the smallest viable next action.

---

## Daily Usage

**Morning (or first session)**
- Update `direction/goals.md` / `projects.md` only if direction itself changed, not because of mood.
- Review or lightly adjust `direction/priorities.md`.
- Log an initial energy sample to `state/energy_log.json`.
- Sketch today’s main track and candidate tasks in `regulation/queue.md`.

**During the day**
- When starting a focus block, update `regulation/focus_block.md`.
- When an event appears, add it to `regulation/interrupts.md` with times and buffers.
- When drifting, log it in `regulation/drift.md` with a return time.
- Let the heartbeat decide whether to:
  - Enter URGENT_INTERRUPT
  - Enter/reset RESET mode
  - Downshift / upshift granularity
  - Nudge you toward the smallest viable start

**End of day**
- Write a brief reflection in `memory/daily/YYYY-MM-DD.md`.
- Update any open loops in `regulation/closure.md`.
- Let `metrics.json` and `energy_log.json` capture streaks and patterns (either manually or via a small script).

---

## Extending OpenClaw

- **Automations:** You can add simple scripts or a small daemon that runs the heartbeat loop, reads these files, and prints minimal prompts.
- **Integrations:** Follow `TOOLS.md` — start local‑only (no external APIs) unless you deliberately extend the rules.
- **Customization:** Adjust rules in `RULES.md` and routines in `routine/` to match your real constraints, but keep:
  - Direction stable.
  - Execution adaptive.
  - Silence the default.

ClawCoach is meant to feel like a quiet, reliable behavior layer, not an attention‑grabbing app. If it talks too much, trim `RULES.md` until most cycles end with `HEARTBEAT_OK`.

