# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import os
import shlex
from pathlib import Path

from kame_agent.exceptions import SafetyError

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    "target",
    "coverage",
    ".pytest_cache",
}

SECRET_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
}

SECRET_SUFFIXES = {".pem", ".key"}
BINARY_CHECK_BYTES = 4096
MAX_FILE_BYTES = 256_000
MAX_CHANGED_FILE_BYTES = 512_000
MAX_TOTAL_CONTEXT_BYTES = 1_500_000

DANGEROUS_FIRST_TOKENS = {
    "rm",
    "sudo",
    "chmod",
    "chown",
    "curl",
    "wget",
    "ssh",
    "scp",
    "rsync",
    "docker",
    "kill",
    "pkill",
    "shutdown",
    "reboot",
}

DANGEROUS_EXACT_PREFIXES = (
    ("git", "push"),
    ("git", "reset", "--hard"),
    ("npm", "publish"),
    ("pip", "install"),
    ("pip3", "install"),
    ("python", "-m", "pip", "install"),
    ("python3", "-m", "pip", "install"),
)

ALLOWED_COMMAND_PREFIXES = (
    ("git", "status"),
    ("git", "diff"),
    ("pytest",),
    ("python", "-m", "pytest"),
    ("python3", "-m", "pytest"),
    ("mypy",),
    ("ruff", "check"),
    ("npm", "test"),
    ("npm", "run", "test"),
    ("npm", "run", "lint"),
    ("npm", "run", "typecheck"),
    ("cargo", "test"),
    ("go", "test"),
    ("make", "test"),
)

SHELL_CONTROL_TOKENS = {"&&", "||", ";", "|", ">", ">>", "<", "$(", "`"}
WRITE_LIKE_FLAGS = {"--fix", "--write", "--force", "--watch"}


def normalize_workspace(workspace: Path) -> Path:
    root = workspace.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise SafetyError(f"Workspace is not a directory: {workspace}")
    return root


def resolve_workspace_path(workspace: Path, relative_path: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise SafetyError(f"Absolute paths are not allowed: {relative_path}")
    if ".." in candidate.parts:
        raise SafetyError(f"Parent traversal is not allowed: {relative_path}")
    resolved = (workspace / candidate).resolve(strict=False)
    try:
        resolved.relative_to(workspace)
    except ValueError as exc:
        raise SafetyError(f"Path escapes workspace: {relative_path}") from exc
    if resolved.exists():
        real = resolved.resolve(strict=True)
        try:
            real.relative_to(workspace)
        except ValueError as exc:
            raise SafetyError(f"Path escapes workspace through symlink: {relative_path}") from exc
    return resolved


def is_excluded_path(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def is_secret_path(path: Path) -> bool:
    name = path.name.lower()
    return name in SECRET_NAMES or path.suffix.lower() in SECRET_SUFFIXES


def is_binary_file(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:BINARY_CHECK_BYTES]
    except OSError:
        return True
    return b"\0" in chunk


def ensure_readable_text_file(workspace: Path, relative_path: str) -> Path:
    path = resolve_workspace_path(workspace, relative_path)
    if not path.exists() or not path.is_file():
        raise SafetyError(f"File does not exist: {relative_path}")
    rel = path.relative_to(workspace)
    if is_excluded_path(rel) or is_secret_path(rel):
        raise SafetyError(f"File is excluded from LLM context: {relative_path}")
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise SafetyError(f"File is too large to read safely: {relative_path}")
    if is_binary_file(path):
        raise SafetyError(f"Binary file cannot be read: {relative_path}")
    return path


def parse_command(command: str) -> list[str]:
    if any(token in command for token in SHELL_CONTROL_TOKENS):
        raise SafetyError(f"Shell control operators are not allowed: {command}")
    try:
        parts = shlex.split(command, posix=(os.name != "nt"))
    except ValueError as exc:
        raise SafetyError(f"Invalid command syntax: {command}") from exc
    parts = [_strip_outer_quotes(part) for part in parts]
    if not parts:
        raise SafetyError("Empty command is not allowed")
    return parts


def _starts_with(parts: list[str], prefix: tuple[str, ...]) -> bool:
    lowered = [part.lower() for part in parts]
    return tuple(lowered[: len(prefix)]) == prefix


def _strip_outer_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def validate_command(command: str) -> list[str]:
    parts = parse_command(command)
    if _is_high_risk_parts(parts):
        raise SafetyError(f"High-risk command requires explicit user approval: {command}")
    if not any(_starts_with(parts, prefix) for prefix in ALLOWED_COMMAND_PREFIXES):
        raise SafetyError(f"Command is not in the inspection allowlist: {command}")
    return parts


def validate_user_approved_command(command: str) -> list[str]:
    return parse_command(command)


def is_high_risk_command(command: str) -> bool:
    parts = parse_command(command)
    return _is_high_risk_parts(parts)


def command_permission_label(command: str) -> str:
    if is_inspection_allowlisted_command(command):
        return "inspection allowlist"
    if is_high_risk_command(command):
        return "high-risk one-time approval"
    return "one-time user approval"


def _is_high_risk_parts(parts: list[str]) -> bool:
    first = parts[0].lower()
    if first in DANGEROUS_FIRST_TOKENS:
        return True
    if any(_starts_with(parts, prefix) for prefix in DANGEROUS_EXACT_PREFIXES):
        return True
    if any(part.lower() in WRITE_LIKE_FLAGS for part in parts):
        return True
    return False


def is_inspection_allowlisted_command(command: str) -> bool:
    try:
        validate_command(command)
    except SafetyError:
        return False
    return True


def is_auto_allowed_command(command: str) -> bool:
    try:
        parts = validate_command(command)
    except SafetyError:
        return False
    lowered = [part.lower() for part in parts]
    return lowered[:2] in (["git", "status"], ["git", "diff"])
