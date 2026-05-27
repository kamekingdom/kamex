# Author: kamekingdom (2026-05-27)

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

ChangeType = Literal["create", "modify"]
ProjectType = Literal["python", "typescript", "rust", "go", "mixed", "unknown"]


@dataclass(frozen=True)
class FileSnapshot:
    path: str
    content: str


@dataclass(frozen=True)
class ProjectInspection:
    workspace: Path
    files: list[str]
    config_files: list[str]
    detected_project_type: ProjectType
    package_manager: str | None
    test_commands: list[str]
    git_status: str | None = None
    git_diff: str | None = None


@dataclass(frozen=True)
class PlannedChange:
    path: str
    change_type: ChangeType
    updated: str


@dataclass(frozen=True)
class ChangeProposal:
    summary: str
    reasoning_summary: str
    detected_project_type: ProjectType
    files_read: list[str]
    commands_to_run: list[str]
    changes: list[PlannedChange]
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str
