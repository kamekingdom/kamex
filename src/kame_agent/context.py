# Author: kamekingdom (2026-06-10)

from __future__ import annotations

import re

MENTION_PATTERN = re.compile(r"(?<!\w)@([A-Za-z0-9_./\\-]+)")


def extract_file_mentions(text: str) -> list[str]:
    mentions: list[str] = []
    for match in MENTION_PATTERN.finditer(text):
        path = match.group(1).strip().strip(".,:;)]}")
        if not path or path in {".", "/"}:
            continue
        normalized = re.sub(r"/+", "/", path.replace("\\", "/"))
        if normalized not in mentions:
            mentions.append(normalized)
    return mentions
