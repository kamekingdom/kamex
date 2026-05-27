# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import ModuleType

from pytest import MonkeyPatch


def load_installer() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "install_kamex.py"
    spec = importlib.util.spec_from_file_location("install_kamex", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_find_repo_root() -> None:
    installer = load_installer()
    root = Path(__file__).resolve().parents[1]

    assert installer.find_repo_root(root / "scripts" / "install_kamex.py") == root


def test_build_pip_install_command_user() -> None:
    installer = load_installer()

    command = installer.build_pip_install_command("repo", use_user=True)

    assert command[1:5] == ["-m", "pip", "install", "--user"]
    assert command[-2:] == ["-e", "repo"]


def test_build_pip_install_command_environment() -> None:
    installer = load_installer()

    command = installer.build_pip_install_command("repo", use_user=False)

    assert "--user" not in command
    assert command[-2:] == ["-e", "repo"]


def test_should_use_user_install_respects_virtualenv(monkeypatch: MonkeyPatch) -> None:
    installer = load_installer()
    monkeypatch.setattr(installer.sys, "prefix", "venv")
    monkeypatch.setattr(installer.sys, "base_prefix", "base")

    assert installer.should_use_user_install(no_user=False) is False


def test_path_contains(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    installer = load_installer()
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + "other")

    assert installer._path_contains(tmp_path) is True
