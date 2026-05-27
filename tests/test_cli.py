# Author: kamekingdom (2026-05-27)

from __future__ import annotations

from io import StringIO
from pathlib import Path

from pytest import CaptureFixture, MonkeyPatch
from rich.console import Console

from kame_agent.cli import _interactive_loop, _print_banner, main, resolve_cli_workspace


def test_version_command(capsys: CaptureFixture[str]) -> None:
    assert main(["version"]) == 0
    captured = capsys.readouterr()
    assert "kamex 0.1.0" in captured.out


def test_version_flag(capsys: CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    captured = capsys.readouterr()
    assert "kamex 0.1.0" in captured.out


def test_help_mentions_kamex(capsys: CaptureFixture[str]) -> None:
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    captured = capsys.readouterr()
    assert "usage: kamex" in captured.out
    assert "--workspace" in captured.out
    assert "--model" in captured.out
    assert "--no-web-search" in captured.out


def test_default_workspace_is_current_directory(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert resolve_cli_workspace(None) == tmp_path


def test_workspace_argument_overrides_current_directory(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    current = tmp_path / "current"
    target = tmp_path / "target"
    current.mkdir()
    target.mkdir()
    monkeypatch.chdir(current)
    assert resolve_cli_workspace(str(target)) == target


def test_banner_can_show_current_model(tmp_path: Path) -> None:
    output = StringIO()
    console = Console(file=output, force_terminal=False)

    _print_banner(console, tmp_path, "gpt-test")

    rendered = output.getvalue()
    assert "Project:" in rendered
    assert "Model: gpt-test" in rendered


def test_interactive_loop_ignores_empty_input(monkeypatch: MonkeyPatch) -> None:
    class DummyAgent:
        calls = 0

        def run_task(self, _instruction: str) -> int:
            self.calls += 1
            return 0

    answers = iter(["", "   ", "exit"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *_args, **_kwargs: next(answers))
    agent = DummyAgent()

    assert _interactive_loop(agent, Console(file=StringIO())) == 0
    assert agent.calls == 0
