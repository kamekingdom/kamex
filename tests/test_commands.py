# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from pytest import MonkeyPatch

from kame_agent.commands import run_user_approved_command


def test_command_timeout_returns_result(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    def fake_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd="python slow.py", timeout=1)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_user_approved_command(tmp_path, "python slow.py", timeout_seconds=1)

    assert result.returncode == -1
    assert "timed out after 1 seconds" in result.stderr


def test_command_start_failure_returns_result(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    def fake_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("missing executable")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_user_approved_command(tmp_path, "missing-command")

    assert result.returncode == -1
    assert "Command failed to start" in result.stderr


def test_command_stdin_is_closed_to_avoid_interactive_hangs(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    captured_kwargs: dict[str, Any] = {}

    def fake_run(*_args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured_kwargs.update(kwargs)
        return subprocess.CompletedProcess(args=["python"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_user_approved_command(tmp_path, "python janken.py")

    assert result.returncode == 0
    assert captured_kwargs["stdin"] is subprocess.DEVNULL
