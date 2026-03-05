#!/usr/bin/env python3
import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Thread, Event
from typing import Optional

import rumps
from dateutil import parser as dtparser
from pynput import keyboard


# -------------------------
# Configuration (edit these)
# -------------------------

# OpenClaw workspace root (where state/state.json exists)
WORKSPACE_DIR = os.path.expanduser("~/.openclaw/workspace")

STATE_PATH = os.path.join(WORKSPACE_DIR, "state", "state.json")

# Polling interval for state.json (seconds)
POLL_INTERVAL_SEC = 15

# When a nudge is due, optionally send NUDGE_CHECK to OpenClaw
SEND_NUDGE_CHECK_EVENT = False
NUDGE_CHECK_TEXT = "NUDGE_CHECK"

# If openclaw isn't on PATH, set absolute path here.
# (Homebrew on Intel often: /usr/local/bin/openclaw)
OPENCLAW_BIN = "openclaw"

# Hotkeys (global)
# Cmd+Shift+L = low energy
# Cmd+Shift+S = start 2 minutes
# Cmd+Shift+P = progress ping
# Cmd+Shift+C = closure paused
# Cmd+Shift+D = drift 30 minutes
HOTKEYS = {
    "<cmd>+<shift>+l": "ENERGY_SET LOW",
    "<cmd>+<shift>+s": "START 2",
    "<cmd>+<shift>+p": "PROGRESS",
    "<cmd>+<shift>+c": "CLOSURE PAUSED",
    "<cmd>+<shift>+d": "DRIFT 30",
}


# -------------------------
# Helpers
# -------------------------

def notify(title: str, message: str) -> None:
    title_esc = title.replace('"', '\\"')
    msg_esc = message.replace('"', '\\"')
    script = f'display notification "{msg_esc}" with title "{title_esc}"'
    subprocess.run(["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_openclaw_event(text: str) -> None:
    cmd = [OPENCLAW_BIN, "system", "event", "--text", text, "--mode", "now"]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        notify("ClawCoach: OpenClaw error", f"Failed to run event:\n{text}\n\n{e}")


def read_state() -> Optional[dict]:
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = dtparser.isoparse(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def compact_status(state: dict) -> str:
    energy = state.get("energy") or "?"
    sub_state = state.get("sub_state") or "NONE"

    dials = state.get("dials") or {}
    gran = dials.get("granularity") or "?"
    box = dials.get("time_box_min") or 0

    cf = state.get("current_focus") or {}
    task_id = cf.get("task_id") or "-"
    action = cf.get("next_action_text") or ""

    # Keep the menubar short; action is shown in menu item below
    return f"{task_id} • {box}m • {energy}/{sub_state} • {gran}"


def current_action_line(state: dict) -> str:
    cf = state.get("current_focus") or {}
    task_id = cf.get("task_id") or "(no task)"
    action = cf.get("next_action_text") or "(no next action yet)"
    return f"Next: {task_id} → {action}"


# -------------------------
# Background watcher thread
# -------------------------

@dataclass
class NudgeStatus:
    last_nudge_for_ts: Optional[datetime] = None


class StateWatcher(Thread):
    def __init__(self, stop_event: Event, status: NudgeStatus, app_ref):
        super().__init__(daemon=True)
        self.stop_event = stop_event
        self.status = status
        self.app_ref = app_ref

    def run(self):
        while not self.stop_event.is_set():
            state = read_state()
            if state:
                # Update menu title + status lines
                self.app_ref.title = "ClawCoach"
                self.app_ref.menu_item_status.title = "Status: " + compact_status(state)
                self.app_ref.menu_item_next.title = current_action_line(state)

                # Nudges based on next_nudge_ts
                next_nudge_ts = parse_ts(state.get("next_nudge_ts"))
                if next_nudge_ts:
                    now = utcnow()
                    due = now >= next_nudge_ts

                    # avoid duplicate notifications for same nudge timestamp
                    already_nudged_this_ts = (
                        self.status.last_nudge_for_ts is not None
                        and abs((self.status.last_nudge_for_ts - next_nudge_ts).total_seconds()) < 1
                    )

                    if due and not already_nudged_this_ts:
                        cf = state.get("current_focus") or {}
                        task_id = cf.get("task_id") or "your task"
                        action = cf.get("next_action_text") or "2 minutes: just open the file."
                        notify("ClawCoach", f"{task_id}\n{action}")
                        self.status.last_nudge_for_ts = next_nudge_ts

                        if SEND_NUDGE_CHECK_EVENT:
                            run_openclaw_event(NUDGE_CHECK_EVENT)

            time.sleep(POLL_INTERVAL_SEC)


# -------------------------
# Hotkeys thread
# -------------------------

class HotkeyListener(Thread):
    def __init__(self, stop_event: Event):
        super().__init__(daemon=True)
        self.stop_event = stop_event
        self.listener = None

    def run(self):
        hotkeys = {k: (lambda cmd=v: run_openclaw_event(cmd)) for k, v in HOTKEYS.items()}
        with keyboard.GlobalHotKeys(hotkeys) as self.listener:
            while not self.stop_event.is_set():
                time.sleep(0.2)
            # listener exits when context manager closes


# -------------------------
# Menubar App
# -------------------------

class ClawCoachApp(rumps.App):
    def __init__(self):
        super().__init__("ClawCoach", quit_button=None)
        self.stop_event = Event()
        self.nudge_status = NudgeStatus()

        # Menu items we update live
        self.menu_item_status = rumps.MenuItem("Status: (loading...)")
        self.menu_item_next = rumps.MenuItem("Next: (loading...)")

        self.menu = [
            self.menu_item_status,
            self.menu_item_next,
            None,

            rumps.MenuItem("Energy → LOW", callback=lambda _: run_openclaw_event("ENERGY_SET LOW")),
            rumps.MenuItem("Energy → MEDIUM", callback=lambda _: run_openclaw_event("ENERGY_SET MEDIUM")),
            rumps.MenuItem("Energy → HIGH", callback=lambda _: run_openclaw_event("ENERGY_SET HIGH")),
            None,

            rumps.MenuItem("Start → 2 minutes", callback=lambda _: run_openclaw_event("START 2")),
            rumps.MenuItem("Start → 10 minutes", callback=lambda _: run_openclaw_event("START 10")),
            rumps.MenuItem("Start → 25 minutes", callback=lambda _: run_openclaw_event("START 25")),
            None,

            rumps.MenuItem("Drift → 10 minutes", callback=lambda _: run_openclaw_event("DRIFT 10")),
            rumps.MenuItem("Drift → 30 minutes", callback=lambda _: run_openclaw_event("DRIFT 30")),
            rumps.MenuItem("Drift → 60 minutes", callback=lambda _: run_openclaw_event("DRIFT 60")),
            None,

            rumps.MenuItem("Progress ping", callback=lambda _: run_openclaw_event("PROGRESS")),
            rumps.MenuItem("Closure → DONE", callback=lambda _: run_openclaw_event("CLOSURE DONE")),
            rumps.MenuItem("Closure → PAUSED", callback=lambda _: run_openclaw_event("CLOSURE PAUSED")),
            None,

            rumps.MenuItem("Show hotkeys", callback=self.show_hotkeys),
            rumps.MenuItem("Open workspace folder", callback=self.open_workspace),
            None,
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]

        # Start watcher + hotkeys
        self.watcher = StateWatcher(self.stop_event, self.nudge_status, self)
        self.watcher.start()

        self.hotkeys = HotkeyListener(self.stop_event)
        self.hotkeys.start()

        # One-time sanity check
        if not os.path.exists(STATE_PATH):
            notify("ClawCoach", f"state.json not found:\n{STATE_PATH}\nEdit WORKSPACE_DIR in clawcoach_menubar.py")
        else:
            notify("ClawCoach", "Menubar running. Hotkeys enabled (requires Accessibility permission).")

    def show_hotkeys(self, _):
        lines = ["Hotkeys:"]
        for k, v in HOTKEYS.items():
            lines.append(f"{k}  →  {v}")
        notify("ClawCoach", "\n".join(lines))

    def open_workspace(self, _):
        subprocess.run(["open", WORKSPACE_DIR])

    def quit_app(self, _):
        self.stop_event.set()
        rumps.quit_application()


if __name__ == "__main__":
    ClawCoachApp().run()

