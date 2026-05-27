# Author: kamekingdom (2026-05-27)

from __future__ import annotations

from pathlib import Path

from kame_agent.exceptions import ProposalError, SafetyError
from kame_agent.models import FileSnapshot, PlannedChange
from kame_agent.safety import (
    MAX_CHANGED_FILE_BYTES,
    ensure_readable_text_file,
    is_secret_path,
    resolve_workspace_path,
)


def read_text_file(workspace: Path, relative_path: str) -> FileSnapshot:
    path = ensure_readable_text_file(workspace, relative_path)
    content = path.read_text(encoding="utf-8", errors="replace")
    return FileSnapshot(path=relative_path, content=content)


def read_existing_or_empty(workspace: Path, relative_path: str) -> str:
    path = resolve_workspace_path(workspace, relative_path)
    if not path.exists():
        return ""
    if not path.is_file():
        raise SafetyError(f"Not a file: {relative_path}")
    return path.read_text(encoding="utf-8", errors="replace")


def validate_change(workspace: Path, change: PlannedChange) -> Path:
    path = resolve_workspace_path(workspace, change.path)
    if is_secret_path(Path(change.path)):
        raise ProposalError(f"Refusing to change secret-like file: {change.path}")
    updated_size = len(change.updated.encode("utf-8"))
    if updated_size > MAX_CHANGED_FILE_BYTES:
        raise ProposalError(f"Refusing oversized change for {change.path}")
    if change.change_type == "modify":
        if not path.exists() or not path.is_file():
            raise ProposalError(f"Cannot modify missing file: {change.path}")
    if change.change_type == "create":
        if path.exists():
            raise ProposalError(f"Cannot create existing file: {change.path}")
    return path


def apply_changes(workspace: Path, changes: list[PlannedChange]) -> None:
    for change in changes:
        validate_change(workspace, change)
    for change in changes:
        path = resolve_workspace_path(workspace, change.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(change.updated, encoding="utf-8", newline="")
