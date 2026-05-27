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
class ReadingPlan:
    files_to_read: list[str]
    web_search_queries: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WebSearchResult:
    query: str
    summary: str
    sources: list[str] = field(default_factory=list)


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


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class UsageCost:
    input_cost_usd: float | None
    output_cost_usd: float | None
    total_cost_usd: float | None


@dataclass(frozen=True)
class UsageTotals:
    runs: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_cost_usd: float | None


def add_token_usage(left: TokenUsage, right: TokenUsage) -> TokenUsage:
    return TokenUsage(
        input_tokens=left.input_tokens + right.input_tokens,
        output_tokens=left.output_tokens + right.output_tokens,
        total_tokens=left.total_tokens + right.total_tokens,
    )
