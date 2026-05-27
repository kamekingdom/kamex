# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import os
from pathlib import Path

from kame_agent.commands import run_auto_command
from kame_agent.models import ProjectInspection, ProjectType
from kame_agent.safety import (
    EXCLUDED_DIRS,
    MAX_TOTAL_CONTEXT_BYTES,
    is_binary_file,
    is_excluded_path,
    is_secret_path,
    normalize_workspace,
)

CONFIG_FILE_NAMES = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "README.md",
    "README.rst",
    "Makefile",
    "Dockerfile",
    "pytest.ini",
    "tsconfig.json",
    ".eslintrc",
    ".eslintrc.json",
    "ruff.toml",
}


def inspect_workspace(workspace: Path) -> ProjectInspection:
    root = normalize_workspace(workspace)
    files: list[str] = []
    config_files: list[str] = []
    total_bytes = 0
    for current_root, dir_names, file_names in os.walk(root):
        dir_names[:] = [name for name in dir_names if name not in EXCLUDED_DIRS]
        current = Path(current_root)
        rel_dir = current.relative_to(root)
        if is_excluded_path(rel_dir):
            continue
        for file_name in sorted(file_names):
            path = current / file_name
            rel = path.relative_to(root)
            rel_str = rel.as_posix()
            if is_secret_path(rel) or is_excluded_path(rel):
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > 512_000 or is_binary_file(path):
                continue
            if total_bytes + size > MAX_TOTAL_CONTEXT_BYTES and file_name not in CONFIG_FILE_NAMES:
                continue
            total_bytes += size
            files.append(rel_str)
            if file_name in CONFIG_FILE_NAMES:
                config_files.append(rel_str)
    detected = detect_project_type(files)
    package_manager = detect_package_manager(files)
    test_commands = infer_test_commands(files, detected)
    git_status = run_auto_command(root, "git status --short")
    git_diff = run_auto_command(root, "git diff --stat")
    return ProjectInspection(
        workspace=root,
        files=sorted(files),
        config_files=sorted(config_files),
        detected_project_type=detected,
        package_manager=package_manager,
        test_commands=test_commands,
        git_status=git_status.stdout.strip() if git_status else None,
        git_diff=git_diff.stdout.strip() if git_diff else None,
    )


def detect_project_type(files: list[str]) -> ProjectType:
    has_python = any(path.endswith((".py", "pyproject.toml", "requirements.txt")) for path in files)
    has_ts = any(path.endswith((".ts", ".tsx", "package.json", "tsconfig.json")) for path in files)
    has_rust = any(path.endswith((".rs", "Cargo.toml")) for path in files)
    has_go = any(path.endswith((".go", "go.mod")) for path in files)
    count = sum([has_python, has_ts, has_rust, has_go])
    if count > 1:
        return "mixed"
    if has_python:
        return "python"
    if has_ts:
        return "typescript"
    if has_rust:
        return "rust"
    if has_go:
        return "go"
    return "unknown"


def detect_package_manager(files: list[str]) -> str | None:
    file_set = set(files)
    if "uv.lock" in file_set:
        return "uv"
    if "poetry.lock" in file_set:
        return "poetry"
    if "requirements.txt" in file_set or "pyproject.toml" in file_set:
        return "python"
    if "pnpm-lock.yaml" in file_set:
        return "pnpm"
    if "yarn.lock" in file_set:
        return "yarn"
    if "package-lock.json" in file_set or "package.json" in file_set:
        return "npm"
    if "Cargo.toml" in file_set:
        return "cargo"
    if "go.mod" in file_set:
        return "go"
    return None


def infer_test_commands(files: list[str], project_type: ProjectType) -> list[str]:
    file_set = set(files)
    commands: list[str] = []
    if project_type in ("python", "mixed"):
        commands.append("python -m pytest")
    if project_type in ("typescript", "mixed") and "package.json" in file_set:
        commands.extend(["npm test", "npm run lint", "npm run typecheck"])
    if project_type in ("rust", "mixed"):
        commands.append("cargo test")
    if project_type in ("go", "mixed"):
        commands.append("go test ./...")
    if "Makefile" in file_set:
        commands.append("make test")
    return commands
