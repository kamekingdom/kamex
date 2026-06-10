# Author: kamekingdom (2026-05-27)

from __future__ import annotations

from io import StringIO
from pathlib import Path

from pytest import CaptureFixture, MonkeyPatch
from rich.console import Console

from kame_agent.cli import (
    _interactive_loop,
    _print_banner,
    build_resume_instruction,
    main,
    print_history,
    resolve_cli_workspace,
)
from kame_agent.session_log import append_session_event


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
    assert "--no-auto-run-safe-commands" in captured.out
    assert "--no-review" in captured.out
    assert "--max-turns" in captured.out
    assert "--max-context-rounds" in captured.out


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


def test_print_history_shows_completed_tasks(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("KAMEX_CONFIG_DIR", str(tmp_path / "config"))
    append_session_event(
        workspace,
        "task_completed",
        {"task": "fix tests", "turns": 2, "changed_files": ["src/app.py"]},
    )
    output = StringIO()

    print_history(Console(file=output), workspace)

    rendered = output.getvalue()
    assert "fix tests" in rendered
    assert "src/app.py" in rendered


def test_build_resume_instruction_mentions_previous_task() -> None:
    instruction = build_resume_instruction("fix tests")

    assert "Resume the most recent kamex task" in instruction
    assert "Previous task:\nfix tests" in instruction


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
