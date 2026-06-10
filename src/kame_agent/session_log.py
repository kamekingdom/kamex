# Author: kamekingdom (2026-06-09)

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kame_agent.config import get_user_config_dir

MAX_SESSION_EVENTS = 200


def append_session_event(workspace: Path, event_type: str, payload: dict[str, Any]) -> Path:
    path = workspace_session_file(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "created_at": datetime.now(UTC).isoformat(),
        "workspace": str(workspace.resolve()),
        "event_type": event_type,
        "payload": payload,
    }
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def read_session_events(workspace: Path, limit: int = MAX_SESSION_EVENTS) -> list[dict[str, Any]]:
    path = workspace_session_file(workspace)
    if not path.exists() or not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events[-limit:]


def latest_task(workspace: Path) -> str | None:
    events = read_session_events(workspace)
    for event in reversed(events):
        if event.get("event_type") not in {"task_started", "task_completed"}:
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        task = payload.get("task")
        if isinstance(task, str) and task.strip():
            return task.strip()
    return None


def read_session_context(workspace: Path, limit: int = 20) -> list[str]:
    context: list[str] = []
    for event in read_session_events(workspace, limit=limit):
        event_type = event.get("event_type")
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        if event_type == "task_started":
            task = payload.get("task")
            if isinstance(task, str):
                context.append(f"Started: {task}")
        elif event_type == "turn_completed":
            summary = payload.get("summary")
            changed = payload.get("changed_files")
            commands = payload.get("commands")
            parts = [f"Turn {payload.get('turn', '?')}: {summary or 'completed'}"]
            if isinstance(changed, list) and changed:
                parts.append("changed " + ", ".join(str(item) for item in changed))
            if isinstance(commands, list) and commands:
                command_bits = []
                for command in commands:
                    if isinstance(command, dict):
                        command_bits.append(f"{command.get('command')} exit {command.get('returncode')}")
                if command_bits:
                    parts.append("commands " + "; ".join(command_bits))
            context.append(" | ".join(parts))
        elif event_type == "task_completed":
            task = payload.get("task")
            turns = payload.get("turns")
            changed = payload.get("changed_files")
            line = f"Completed: {task or '-'} in {turns or '?'} turns"
            if isinstance(changed, list) and changed:
                line += "; changed " + ", ".join(str(item) for item in changed)
            context.append(line)
    return context[-limit:]


def workspace_session_file(workspace: Path) -> Path:
    digest = hashlib.sha256(str(workspace.resolve()).encode("utf-8")).hexdigest()[:16]
    return get_user_config_dir() / "sessions" / f"{digest}.jsonl"
