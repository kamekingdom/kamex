# Author: kamekingdom (2026-05-27)

from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from kame_agent.config import DEFAULT_MODEL, get_user_config_file, load_config, save_openai_api_key


def test_save_openai_api_key_to_user_config(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("KAMEX_CONFIG_DIR", str(config_dir))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    saved_path = save_openai_api_key("sk-test")

    assert saved_path == config_dir / ".env"
    assert get_user_config_file() == config_dir / ".env"
    assert "OPENAI_API_KEY" in saved_path.read_text(encoding="utf-8")
    assert not (workspace / ".env").exists()
    assert load_config(workspace).api_key == "sk-test"


def test_environment_api_key_overrides_saved_config(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("KAMEX_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    save_openai_api_key("sk-saved")

    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")

    assert load_config(workspace).api_key == "sk-env"


def test_workspace_env_overrides_saved_config_when_process_env_is_empty(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".env").write_text('OPENAI_API_KEY="sk-workspace"\n', encoding="utf-8")
    monkeypatch.setenv("KAMEX_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    save_openai_api_key("sk-saved")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert load_config(workspace).api_key == "sk-workspace"


def test_default_model_is_codex_optimized(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("KAMEX_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    assert load_config(workspace).model == DEFAULT_MODEL
    assert DEFAULT_MODEL.endswith("-codex")
