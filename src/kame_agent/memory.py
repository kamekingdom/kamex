# Author: kamekingdom (2026-06-09)

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kame_agent.config import get_user_config_dir

MAX_MEMORY_ITEMS = 20
MAX_MEMORY_TEXT_CHARS = 1_000


def read_workspace_memory(workspace: Path, limit: int = MAX_MEMORY_ITEMS) -> list[str]:
    path = workspace_memory_file(workspace)
    if not path.exists() or not path.is_file():
        return []
    items: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = data.get("text")
        if isinstance(text, str) and text.strip():
            items.append(text.strip())
    return items[-limit:]


def append_workspace_memory(workspace: Path, text: str) -> Path:
    cleaned = text.strip()
    if not cleaned:
        return workspace_memory_file(workspace)
    if len(cleaned) > MAX_MEMORY_TEXT_CHARS:
        cleaned = cleaned[:MAX_MEMORY_TEXT_CHARS].rstrip() + "..."
    path = workspace_memory_file(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    event: dict[str, Any] = {
        "created_at": datetime.now(UTC).isoformat(),
        "workspace": str(workspace.resolve()),
        "text": cleaned,
    }
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def workspace_memory_file(workspace: Path) -> Path:
    digest = hashlib.sha256(str(workspace.resolve()).encode("utf-8")).hexdigest()[:16]
    return get_user_config_dir() / "memory" / f"{digest}.jsonl"
