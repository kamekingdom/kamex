# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import os
from pathlib import Path

import pytest

from kame_agent.exceptions import SafetyError
from kame_agent.fs import read_text_file
from kame_agent.safety import (
    command_permission_label,
    ensure_readable_text_file,
    validate_command,
    validate_user_approved_command,
)


def test_rejects_parent_traversal(tmp_path: Path) -> None:
    with pytest.raises(SafetyError):
        ensure_readable_text_file(tmp_path, "../outside.txt")


def test_rejects_workspace_escape_absolute_path(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(SafetyError):
        ensure_readable_text_file(tmp_path, str(outside.resolve()))


def test_rejects_symlink_to_outside_workspace(tmp_path: Path) -> None:
    outside = tmp_path.parent / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable in this environment")
    with pytest.raises(SafetyError):
        ensure_readable_text_file(tmp_path, "link.txt")


def test_secret_file_is_not_read_for_llm_context(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("OPENAI_API_KEY=secret", encoding="utf-8")
    with pytest.raises(SafetyError):
        read_text_file(tmp_path, ".env")


@pytest.mark.parametrize(
    "command",
    [
        "rm -rf .",
        "sudo pytest",
        "curl https://example.com",
        "git push",
        "git reset --hard",
        "npm publish",
        "pip install requests",
        "python -m pip install requests",
        "docker ps",
        "pytest && rm -rf .",
        "ruff check --fix",
    ],
)
def test_rejects_dangerous_commands(command: str) -> None:
    with pytest.raises(SafetyError):
        validate_command(command)


@pytest.mark.parametrize(
    "command",
    [
        "git status --short",
        "git diff",
        "pytest",
        "python -m pytest",
        "mypy src",
        "ruff check src",
        "npm test",
        "npm run lint",
        "npm run typecheck",
        "cargo test",
        "go test ./...",
        "make test",
    ],
)
def test_allows_inspection_commands(command: str) -> None:
    assert validate_command(command)


@pytest.mark.parametrize(
    "command",
    [
        "python janken.py",
        "rm -rf .",
        "pip install requests",
        "python -m pip install requests",
        "ruff check --fix",
    ],
)
def test_user_approved_command_can_be_outside_inspection_allowlist(command: str) -> None:
    assert validate_user_approved_command(command)


@pytest.mark.parametrize(
    "command",
    [
        "pytest && rm -rf .",
        "pytest | more",
        "pytest > out.txt",
    ],
)
def test_user_approved_command_still_rejects_shell_control_commands(command: str) -> None:
    with pytest.raises(SafetyError):
        validate_user_approved_command(command)


@pytest.mark.parametrize(
    ("command", "label"),
    [
        ("python -m pytest", "inspection allowlist"),
        ("python janken.py", "one-time user approval"),
        ("rm -rf .", "high-risk one-time approval"),
        ("pip install requests", "high-risk one-time approval"),
    ],
)
def test_command_permission_label(command: str, label: str) -> None:
    assert command_permission_label(command) == label
