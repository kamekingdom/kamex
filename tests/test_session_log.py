# Author: kamekingdom (2026-06-09)

from __future__ import annotations

import json
from pathlib import Path

from pytest import MonkeyPatch

from kame_agent.session_log import (
    append_session_event,
    latest_task,
    read_session_context,
    read_session_events,
    workspace_session_file,
)


def test_append_session_event_writes_workspace_jsonl(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    workspace = tmp_path / "project"
    workspace.mkdir()
    monkeypatch.setenv("KAMEX_CONFIG_DIR", str(config_dir))

    path = append_session_event(workspace, "task_started", {"task": "fix tests"})

    assert path == workspace_session_file(workspace)
    assert path.parent == config_dir / "sessions"
    line = path.read_text(encoding="utf-8").strip()
    event = json.loads(line)
    assert event["event_type"] == "task_started"
    assert event["payload"] == {"task": "fix tests"}
    assert event["workspace"] == str(workspace.resolve())


def test_read_session_events_returns_recent_events(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()
    monkeypatch.setenv("KAMEX_CONFIG_DIR", str(tmp_path / "config"))

    append_session_event(workspace, "task_started", {"task": "one"})
    append_session_event(workspace, "task_completed", {"task": "two"})

    events = read_session_events(workspace, limit=1)

    assert len(events) == 1
    assert events[0]["event_type"] == "task_completed"


def test_latest_task_and_session_context(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()
    monkeypatch.setenv("KAMEX_CONFIG_DIR", str(tmp_path / "config"))

    append_session_event(workspace, "task_started", {"task": "fix tests"})
    append_session_event(
        workspace,
        "turn_completed",
        {
            "turn": 1,
            "summary": "Updated parser",
            "changed_files": ["src/parser.py"],
            "commands": [{"command": "python -m pytest", "returncode": 0}],
        },
    )
    append_session_event(workspace, "task_completed", {"task": "fix tests", "turns": 1})

    assert latest_task(workspace) == "fix tests"
    context = read_session_context(workspace)
    assert any("Started: fix tests" in item for item in context)
    assert any("Updated parser" in item and "python -m pytest exit 0" in item for item in context)
