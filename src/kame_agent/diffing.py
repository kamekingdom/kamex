# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import difflib
from pathlib import Path

from kame_agent.fs import read_existing_or_empty, validate_change
from kame_agent.models import PlannedChange


def generate_diff(workspace: Path, changes: list[PlannedChange]) -> str:
    chunks: list[str] = []
    for change in changes:
        validate_change(workspace, change)
        original = read_existing_or_empty(workspace, change.path)
        from_name = f"a/{change.path}"
        to_name = f"b/{change.path}"
        if change.change_type == "create":
            from_name = "/dev/null"
        lines = difflib.unified_diff(
            original.splitlines(),
            change.updated.splitlines(),
            fromfile=from_name,
            tofile=to_name,
            lineterm="",
        )
        chunks.append("\n".join(lines))
    return "\n".join(chunk for chunk in chunks if chunk)
