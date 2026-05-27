# Author: kamekingdom (2026-05-27)

from __future__ import annotations

from pathlib import Path

import pytest

from kame_agent.diffing import generate_diff
from kame_agent.exceptions import ProposalError
from kame_agent.fs import apply_changes, validate_change
from kame_agent.models import PlannedChange


def test_generate_diff_does_not_modify_before_approval(tmp_path: Path) -> None:
    target = tmp_path / "hello.txt"
    target.write_text("old\n", encoding="utf-8")
    change = PlannedChange(path="hello.txt", change_type="modify", updated="new\n")
    diff = generate_diff(tmp_path, [change])
    assert "-old" in diff
    assert "+new" in diff
    assert target.read_text(encoding="utf-8") == "old\n"


def test_apply_changes_modifies_after_approval(tmp_path: Path) -> None:
    target = tmp_path / "hello.txt"
    target.write_text("old\n", encoding="utf-8")
    change = PlannedChange(path="hello.txt", change_type="modify", updated="new\n")
    apply_changes(tmp_path, [change])
    assert target.read_text(encoding="utf-8") == "new\n"


def test_create_new_file(tmp_path: Path) -> None:
    change = PlannedChange(path="docs/new.md", change_type="create", updated="# New\n")
    apply_changes(tmp_path, [change])
    assert (tmp_path / "docs" / "new.md").read_text(encoding="utf-8") == "# New\n"


def test_create_existing_file_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "existing.txt").write_text("x", encoding="utf-8")
    change = PlannedChange(path="existing.txt", change_type="create", updated="y")
    with pytest.raises(ProposalError):
        validate_change(tmp_path, change)


def test_modify_missing_file_is_rejected(tmp_path: Path) -> None:
    change = PlannedChange(path="missing.txt", change_type="modify", updated="x")
    with pytest.raises(ProposalError):
        validate_change(tmp_path, change)
