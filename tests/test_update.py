# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import json
from typing import Any

from pytest import MonkeyPatch

from kame_agent.update import (
    build_update_command,
    check_for_update,
    compare_versions,
    fetch_latest_version,
    normalize_version,
    parse_version_from_text,
)


def test_compare_versions() -> None:
    assert compare_versions("0.2.0", "0.1.9") == 1
    assert compare_versions("1.0", "1.0.0") == 0
    assert compare_versions("0.1.0", "0.2.0") == -1


def test_normalize_version() -> None:
    assert normalize_version("v1.2.3") == "1.2.3"
    assert normalize_version("release-2.0") == "2.0"
    assert normalize_version("latest") is None


def test_parse_version_from_text() -> None:
    assert parse_version_from_text('version = "0.3.0"') == "0.3.0"
    assert parse_version_from_text('__version__ = "0.4.0"') == "0.4.0"


def test_fetch_latest_version_from_github_json(monkeypatch: MonkeyPatch) -> None:
    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"tag_name": "v9.8.7"}).encode("utf-8")

    def fake_urlopen(*_args: Any, **_kwargs: Any) -> FakeResponse:
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    assert fetch_latest_version("https://example.test/releases/latest") == "9.8.7"


def test_check_for_update_can_be_disabled(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("KAMEX_DISABLE_UPDATE_CHECK", "1")

    assert check_for_update("0.1.0") is None


def test_check_for_update_returns_info(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("KAMEX_DISABLE_UPDATE_CHECK", raising=False)
    monkeypatch.setenv("KAMEX_UPDATE_INSTALL_SPEC", "git+https://example.test/kamex.git")
    monkeypatch.setattr("kame_agent.update.fetch_latest_version", lambda _url: "0.2.0")

    info = check_for_update("0.1.0")

    assert info is not None
    assert info.latest_version == "0.2.0"
    assert "pip install --upgrade git+https://example.test/kamex.git" in info.install_command


def test_build_update_command_quotes_python_executable(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("sys.executable", "C:\\Program Files\\Python\\python.exe")

    command = build_update_command("git+https://example.test/kamex.git")

    assert command.startswith('"C:\\Program Files\\Python\\python.exe" -m pip install --upgrade ')
