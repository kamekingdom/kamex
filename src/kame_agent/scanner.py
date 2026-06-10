# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import os
from pathlib import Path

from kame_agent.commands import run_auto_command
from kame_agent.models import ProjectInspection, ProjectType
from kame_agent.safety import (
    EXCLUDED_DIRS,
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

INSTRUCTION_FILE_NAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "KAMEX.md",
}

MAX_INSPECTION_FILES = 250
MAX_VISITED_FILES = 5_000
MAX_SCAN_DEPTH = 6
MAX_INSTRUCTION_FILES = 20
MAX_INSTRUCTION_FILE_BYTES = 64_000
MAX_SEARCH_SNIPPETS = 40
MAX_SEARCH_SNIPPETS_PER_FILE = 2
MAX_SEARCH_LINE_CHARS = 220

TASK_KEYWORD_SUFFIXES = {
    "python": {".py", ".toml", ".txt", ".md"},
    "pytest": {".py", ".toml", ".ini"},
    "test": {".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go", ".toml", ".json"},
    "lint": {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".toml"},
    "typescript": {".ts", ".tsx", ".json", ".md"},
    "readme": {".md", ".rst"},
    "docs": {".md", ".rst"},
}

KNOWN_TASK_KEYWORDS = {
    "python",
    "pytest",
    "test",
    "lint",
    "typescript",
    "readme",
    "docs",
}


def inspect_workspace(workspace: Path, task: str | None = None) -> ProjectInspection:
    root = normalize_workspace(workspace)
    candidates: list[tuple[int, str]] = []
    config_files: list[str] = []
    project_instructions: dict[str, str] = {}
    search_snippets: list[str] = []
    visited_files = 0
    task_terms = task_keywords(task or "")
    content_terms = content_search_terms(task or "")
    for current_root, dir_names, file_names in os.walk(root):
        dir_names[:] = [name for name in dir_names if name not in EXCLUDED_DIRS]
        current = Path(current_root)
        rel_dir = current.relative_to(root)
        if is_excluded_path(rel_dir):
            continue
        if len(rel_dir.parts) > MAX_SCAN_DEPTH:
            dir_names[:] = []
            continue
        for file_name in sorted(file_names):
            visited_files += 1
            if visited_files > MAX_VISITED_FILES:
                dir_names[:] = []
                break
            path = current / file_name
            rel = path.relative_to(root)
            rel_str = rel.as_posix()
            if is_secret_path(rel) or is_excluded_path(rel):
                continue
            is_config = file_name in CONFIG_FILE_NAMES and (
                len(rel.parts) <= 2 or is_task_relevant_file(rel_str, task_terms)
            )
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > 512_000 or is_binary_file(path):
                continue
            if file_name in INSTRUCTION_FILE_NAMES and len(project_instructions) < MAX_INSTRUCTION_FILES:
                instruction = read_instruction_file(path, size)
                if instruction:
                    project_instructions[rel_str] = instruction
            snippets = find_content_snippets(path, rel_str, content_terms)
            if snippets and len(search_snippets) < MAX_SEARCH_SNIPPETS:
                search_snippets.extend(snippets[: MAX_SEARCH_SNIPPETS - len(search_snippets)])
            priority = file_priority(rel_str, is_config, task_terms, has_content_match=bool(snippets))
            candidates.append((priority, rel_str))
            if is_config:
                config_files.append(rel_str)
    files = [path for _priority, path in sorted(candidates)[:MAX_INSPECTION_FILES]]
    detected = detect_project_type(files)
    package_manager = detect_package_manager(files)
    test_commands = infer_test_commands(files, detected)
    git_status = run_auto_command(root, "git status --short")
    git_diff = run_auto_command(root, "git diff --stat")
    return ProjectInspection(
        workspace=root,
        files=files,
        config_files=sorted(config_files),
        detected_project_type=detected,
        package_manager=package_manager,
        test_commands=test_commands,
        git_status=git_status.stdout.strip() if git_status else None,
        git_diff=git_diff.stdout.strip() if git_diff else None,
        project_instructions=dict(sorted(project_instructions.items())),
        search_snippets=search_snippets,
    )


def read_instruction_file(path: Path, size: int) -> str:
    if size > MAX_INSTRUCTION_FILE_BYTES:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def file_priority(relative_path: str, is_config: bool, terms: set[str], has_content_match: bool = False) -> int:
    if Path(relative_path).name in INSTRUCTION_FILE_NAMES:
        return 0
    if is_config:
        return 1
    if has_content_match or is_task_relevant_file(relative_path, terms):
        return 2
    return 3


def content_search_terms(task: str) -> list[str]:
    stop_words = {
        "please",
        "update",
        "change",
        "fix",
        "create",
        "make",
        "this",
        "that",
        "with",
        "from",
        "して",
        "ください",
        "この",
        "その",
    }
    terms: list[str] = []
    for word in _split_words(task.lower()):
        if len(word) < 3 or word in stop_words:
            continue
        if word not in terms:
            terms.append(word)
        if len(terms) >= 12:
            break
    return terms


def find_content_snippets(path: Path, relative_path: str, terms: list[str]) -> list[str]:
    if not terms:
        return []
    snippets: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    lowered_terms = [term.lower() for term in terms]
    for line_number, line in enumerate(lines, start=1):
        lowered = line.lower()
        if not any(term in lowered for term in lowered_terms):
            continue
        snippet = line.strip()
        if len(snippet) > MAX_SEARCH_LINE_CHARS:
            snippet = snippet[:MAX_SEARCH_LINE_CHARS].rstrip() + "..."
        snippets.append(f"{relative_path}:{line_number}: {snippet}")
        if len(snippets) >= MAX_SEARCH_SNIPPETS_PER_FILE:
            break
    return snippets


def task_keywords(task: str) -> set[str]:
    lowered = task.lower()
    words = {part for part in _split_words(lowered) if len(part) >= 3}
    terms = words & KNOWN_TASK_KEYWORDS
    if any(word in lowered for word in ("作成", "作って", "作る", "新規", "create", "new")):
        terms.add("create")
    for keyword in ("readme", "pytest", "python", "typescript", "lint"):
        if keyword in lowered:
            terms.add(keyword)
    if "じゃんけん" in lowered:
        terms.update({"python", "game"})
    if "テスト" in lowered:
        terms.add("test")
    if "型" in lowered:
        terms.add("type")
    return terms


def is_task_relevant_file(relative_path: str, terms: set[str]) -> bool:
    if not terms:
        return False
    path = relative_path.lower()
    suffix = Path(path).suffix
    name_parts = set(_split_words(path.replace("/", " ")))
    if terms & name_parts:
        return True
    if "readme" in terms and Path(path).name.startswith("readme"):
        return True
    if "test" in terms and ("test" in name_parts or "tests" in name_parts):
        return True
    if "type" in terms and Path(path).name in {"tsconfig.json", "pyrightconfig.json", "mypy.ini"}:
        return True
    for term in terms:
        suffixes = TASK_KEYWORD_SUFFIXES.get(term)
        if suffixes and suffix in suffixes:
            return True
    return False


def _split_words(text: str) -> list[str]:
    normalized = "".join(char if char.isalnum() else " " for char in text)
    return normalized.split()


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
