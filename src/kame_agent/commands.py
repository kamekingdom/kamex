# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import subprocess
from pathlib import Path

from kame_agent.models import CommandResult
from kame_agent.safety import is_auto_allowed_command, validate_command, validate_user_approved_command

COMMAND_TIMEOUT_SECONDS = 120


def run_command(workspace: Path, command: str, timeout_seconds: int = COMMAND_TIMEOUT_SECONDS) -> CommandResult:
    parts = validate_command(command)
    return _run_parts(workspace, command, parts, timeout_seconds)


def run_user_approved_command(
    workspace: Path,
    command: str,
    timeout_seconds: int = COMMAND_TIMEOUT_SECONDS,
) -> CommandResult:
    parts = validate_user_approved_command(command)
    return _run_parts(workspace, command, parts, timeout_seconds)


def _run_parts(
    workspace: Path,
    command: str,
    parts: list[str],
    timeout_seconds: int,
) -> CommandResult:
    completed = subprocess.run(
        parts,
        cwd=workspace,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        shell=False,
        check=False,
    )
    return CommandResult(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_auto_command(workspace: Path, command: str) -> CommandResult | None:
    if not is_auto_allowed_command(command):
        return None
    try:
        return run_command(workspace, command, timeout_seconds=20)
    except (OSError, subprocess.SubprocessError):
        return None
