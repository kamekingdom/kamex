# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "gpt-5.3-codex"
USER_CONFIG_DIR_ENV = "KAMEX_CONFIG_DIR"
USER_CONFIG_FILE_NAME = ".env"


@dataclass(frozen=True)
class AppConfig:
    api_key: str
    model: str


def load_dotenv_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def read_dotenv_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists() or not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def load_config(workspace: Path, model_override: str | None = None) -> AppConfig:
    user_values = read_dotenv_values(get_user_config_file())
    cwd_values = read_dotenv_values(Path.cwd() / ".env")
    workspace_values = read_dotenv_values(workspace / ".env")
    api_key = _first_config_value("OPENAI_API_KEY", workspace_values, cwd_values, user_values)
    model = model_override or _first_config_value("OPENAI_MODEL", workspace_values, cwd_values, user_values) or DEFAULT_MODEL
    return AppConfig(api_key=api_key, model=model)


def get_user_config_dir() -> Path:
    override = os.environ.get(USER_CONFIG_DIR_ENV)
    if override:
        return Path(override).expanduser()
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "kamex"
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "kamex"
    return Path.home() / ".config" / "kamex"


def get_user_config_file() -> Path:
    return get_user_config_dir() / USER_CONFIG_FILE_NAME


def save_openai_api_key(api_key: str) -> Path:
    cleaned = api_key.strip()
    if not cleaned:
        raise ValueError("OPENAI_API_KEY cannot be empty.")
    config_file = get_user_config_file()
    values = read_dotenv_values(config_file)
    values["OPENAI_API_KEY"] = cleaned
    _write_dotenv_values(config_file, values)
    os.environ["OPENAI_API_KEY"] = cleaned
    return config_file


def _first_config_value(key: str, *dotenv_values: dict[str, str]) -> str:
    env_value = os.environ.get(key)
    if env_value:
        return env_value
    for values in dotenv_values:
        value = values.get(key)
        if value:
            return value
    return ""


def _write_dotenv_values(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={_quote_dotenv_value(value)}" for key, value in sorted(values.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _quote_dotenv_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
