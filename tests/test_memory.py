# Author: kamekingdom (2026-06-09)

from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from kame_agent.memory import append_workspace_memory, read_workspace_memory, workspace_memory_file


def test_workspace_memory_round_trips_by_workspace(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    workspace = tmp_path / "project"
    workspace.mkdir()
    monkeypatch.setenv("KAMEX_CONFIG_DIR", str(config_dir))

    path = append_workspace_memory(workspace, "Task: fix tests\nResult: passed")

    assert path == workspace_memory_file(workspace)
    assert path.parent == config_dir / "memory"
    assert read_workspace_memory(workspace) == ["Task: fix tests\nResult: passed"]


def test_workspace_memory_returns_recent_items(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()
    monkeypatch.setenv("KAMEX_CONFIG_DIR", str(tmp_path / "config"))

    append_workspace_memory(workspace, "one")
    append_workspace_memory(workspace, "two")
    append_workspace_memory(workspace, "three")

    assert read_workspace_memory(workspace, limit=2) == ["two", "three"]
