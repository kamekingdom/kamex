# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_RELEASE_API_URL = "https://api.github.com/repos/kamekingdom/kamex/releases/latest"
DEFAULT_INSTALL_SPEC = "git+https://github.com/kamekingdom/kamex.git"
UPDATE_URL_ENV = "KAMEX_UPDATE_URL"
UPDATE_INSTALL_SPEC_ENV = "KAMEX_UPDATE_INSTALL_SPEC"
DISABLE_UPDATE_CHECK_ENV = "KAMEX_DISABLE_UPDATE_CHECK"
HTTP_TIMEOUT_SECONDS = 2


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    install_command: str
    source_url: str


def check_for_update(current_version: str) -> UpdateInfo | None:
    if _env_truthy(DISABLE_UPDATE_CHECK_ENV):
        return None
    source_url = os.environ.get(UPDATE_URL_ENV, DEFAULT_RELEASE_API_URL)
    latest_version = fetch_latest_version(source_url)
    if latest_version is None:
        return None
    if compare_versions(latest_version, current_version) <= 0:
        return None
    install_spec = os.environ.get(UPDATE_INSTALL_SPEC_ENV, DEFAULT_INSTALL_SPEC)
    return UpdateInfo(
        current_version=current_version,
        latest_version=latest_version,
        install_command=build_update_command(install_spec),
        source_url=source_url,
    )


def fetch_latest_version(source_url: str) -> str | None:
    request = urllib.request.Request(
        source_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "kamex-update-check",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (OSError, urllib.error.URLError, TimeoutError):
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return parse_version_from_text(raw)
    if isinstance(payload, dict):
        for key in ("tag_name", "name", "version"):
            value = payload.get(key)
            if isinstance(value, str):
                parsed = normalize_version(value)
                if parsed:
                    return parsed
    return None


def build_update_command(install_spec: str) -> str:
    executable = _quote_command_part(sys.executable)
    return f"{executable} -m pip install --upgrade {install_spec}"


def compare_versions(left: str, right: str) -> int:
    left_parts = _version_parts(left)
    right_parts = _version_parts(right)
    max_len = max(len(left_parts), len(right_parts))
    left_parts.extend([0] * (max_len - len(left_parts)))
    right_parts.extend([0] * (max_len - len(right_parts)))
    if left_parts > right_parts:
        return 1
    if left_parts < right_parts:
        return -1
    return 0


def normalize_version(value: str) -> str | None:
    match = re.search(r"v?(\d+(?:\.\d+){0,3})", value.strip())
    if not match:
        return None
    return match.group(1)


def parse_version_from_text(text: str) -> str | None:
    patterns = (
        r'version\s*=\s*["\']([^"\']+)["\']',
        r'__version__\s*=\s*["\']([^"\']+)["\']',
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_version(match.group(1))
    return normalize_version(text)


def _version_parts(version: str) -> list[int]:
    normalized = normalize_version(version)
    if normalized is None:
        return [0]
    return [int(part) for part in normalized.split(".")]


def _env_truthy(key: str) -> bool:
    value = os.environ.get(key, "")
    return value.lower() in {"1", "true", "yes", "on"}


def _quote_command_part(value: str) -> str:
    if not value or any(char.isspace() for char in value):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value
