# Author: kamekingdom (2026-05-27)

from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any

from pytest import MonkeyPatch
from rich.console import Console

from kame_agent.agent import KameAgent, TaskTurnResult
from kame_agent.models import ChangeProposal, CommandResult, PlannedChange, ProjectInspection, ReadingPlan


def test_sanitize_proposal_keeps_user_approved_commands(tmp_path: Path) -> None:
    agent = KameAgent(workspace=tmp_path, console=Console(file=StringIO()))
    inspection = _inspection(tmp_path)
    proposal = ChangeProposal(
        summary="Create game",
        reasoning_summary="The user asked for a small game.",
        detected_project_type="python",
        files_read=[],
        commands_to_run=["python janken.py", "python -m pytest"],
        changes=[
            PlannedChange(
                path="janken.py",
                change_type="create",
                updated="print('rock paper scissors')\n",
            )
        ],
    )

    sanitized = agent._sanitize_proposal(inspection, proposal)

    assert sanitized.commands_to_run == ["python janken.py", "python -m pytest"]
    assert any("one-time user approval" in note and "python janken.py" in note for note in sanitized.notes)
    assert sanitized.changes == proposal.changes


def test_sanitize_proposal_keeps_high_risk_commands_for_approval(tmp_path: Path) -> None:
    agent = KameAgent(workspace=tmp_path, console=Console(file=StringIO()))
    inspection = _inspection(tmp_path)
    proposal = ChangeProposal(
        summary="High-risk command",
        reasoning_summary="High-risk commands need explicit approval.",
        detected_project_type="unknown",
        files_read=[],
        commands_to_run=["rm -rf .", "python janken.py"],
        changes=[],
    )

    sanitized = agent._sanitize_proposal(inspection, proposal)

    assert sanitized.commands_to_run == ["rm -rf .", "python janken.py"]
    assert any("high-risk one-time approval" in note and "rm -rf" in note for note in sanitized.notes)


def test_sanitize_proposal_filters_invalid_shell_control_commands(tmp_path: Path) -> None:
    agent = KameAgent(workspace=tmp_path, console=Console(file=StringIO()))
    inspection = _inspection(tmp_path)
    proposal = ChangeProposal(
        summary="Invalid command",
        reasoning_summary="Shell control operators are not accepted.",
        detected_project_type="unknown",
        files_read=[],
        commands_to_run=["pytest && rm -rf .", "python janken.py"],
        changes=[],
    )

    sanitized = agent._sanitize_proposal(inspection, proposal)

    assert sanitized.commands_to_run == ["python janken.py"]
    assert any("Skipped invalid command" in note and "pytest &&" in note for note in sanitized.notes)


def test_print_command_result_treats_output_as_plain_text(tmp_path: Path) -> None:
    output = StringIO()
    agent = KameAgent(workspace=tmp_path, console=Console(file=output, force_terminal=True, width=80))
    result = CommandResult(
        command="git diff --stat",
        returncode=1,
        stdout="file [abc].py | 1 +\n",
        stderr="closing-looking tag [/not-open]\n",
    )

    agent._print_command_result(result)

    rendered = output.getvalue()
    assert "closing-looking tag" in rendered
    assert "git diff --stat" in rendered


def test_should_continue_after_failed_command(tmp_path: Path) -> None:
    agent = KameAgent(workspace=tmp_path, console=Console(file=StringIO()))
    result = TaskTurnResult(
        proposal=_proposal(changes=[]),
        changes_applied=False,
        command_results=[CommandResult("python -m pytest", 1, "", "failed")],
    )

    assert agent._should_continue(result)


def test_should_continue_after_unverified_changes(tmp_path: Path) -> None:
    agent = KameAgent(workspace=tmp_path, console=Console(file=StringIO()))
    result = TaskTurnResult(
        proposal=_proposal(
            changes=[
                PlannedChange(
                    path="app.py",
                    change_type="create",
                    updated="print('ok')\n",
                )
            ]
        ),
        changes_applied=True,
        command_results=[],
    )

    assert agent._should_continue(result)


def test_should_stop_after_successful_command(tmp_path: Path) -> None:
    agent = KameAgent(workspace=tmp_path, console=Console(file=StringIO()))
    result = TaskTurnResult(
        proposal=_proposal(commands=["python -m pytest"]),
        changes_applied=True,
        command_results=[CommandResult("python -m pytest", 0, "passed", "")],
    )

    assert not agent._should_continue(result)


def test_follow_up_task_includes_command_observations(tmp_path: Path) -> None:
    agent = KameAgent(workspace=tmp_path, console=Console(file=StringIO()))
    result = TaskTurnResult(
        proposal=_proposal(summary="Fixed parser"),
        changes_applied=True,
        command_results=[CommandResult("python -m pytest", 1, "", "AssertionError")],
    )

    follow_up = agent._build_follow_up_task("Fix tests", result)

    assert "Original task:" in follow_up
    assert "Fix tests" in follow_up
    assert "Command: python -m pytest" in follow_up
    assert "AssertionError" in follow_up


def test_merge_files_to_read_prioritizes_user_mentions(tmp_path: Path) -> None:
    agent = KameAgent(workspace=tmp_path, console=Console(file=StringIO()))

    files = agent._merge_files_to_read(["README.md", "src/app.py"], ["src/app.py", "tests/test_app.py"])

    assert files == ["src/app.py", "tests/test_app.py", "README.md"]


def test_expand_file_context_reads_additional_files(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('app')\n", encoding="utf-8")
    (tmp_path / "test_app.py").write_text("def test_app(): pass\n", encoding="utf-8")
    inspection = ProjectInspection(
        workspace=tmp_path,
        files=["app.py", "test_app.py"],
        config_files=[],
        detected_project_type="python",
        package_manager=None,
        test_commands=[],
    )

    class DummyClient:
        calls = 0

        def create_context_expansion_plan(
            self,
            _task: str,
            _inspection: ProjectInspection,
            file_context: dict[str, str],
        ) -> ReadingPlan:
            self.calls += 1
            if "test_app.py" in file_context:
                return ReadingPlan(files_to_read=[])
            return ReadingPlan(files_to_read=["test_app.py"])

    agent = KameAgent(workspace=tmp_path, console=Console(file=StringIO()), max_context_expansion_rounds=2)

    context = agent._expand_file_context("fix app", DummyClient(), inspection, {"app.py": "print('app')\n"})

    assert "test_app.py" in context
    assert context["test_app.py"] == "def test_app(): pass\n"


def test_handle_commands_auto_runs_inspection_allowlist(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    output = StringIO()
    agent = KameAgent(workspace=tmp_path, console=Console(file=output))
    inspection = _inspection(tmp_path)

    def fake_run_command(workspace: Path, command: str) -> CommandResult:
        assert workspace == tmp_path
        assert command == "python -m pytest"
        return CommandResult(command=command, returncode=0, stdout="passed", stderr="")

    def fail_confirm(*_args: Any, **_kwargs: Any) -> bool:
        raise AssertionError("safe allowlisted command should not ask for confirmation")

    monkeypatch.setattr("kame_agent.agent.run_command", fake_run_command)
    monkeypatch.setattr("rich.prompt.Confirm.ask", fail_confirm)

    results = agent._handle_commands(inspection, ["python -m pytest"])

    assert len(results) == 1
    assert results[0].returncode == 0
    assert "Auto-running safe command" in output.getvalue()


def test_handle_commands_can_prompt_for_allowlist_when_auto_run_disabled(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    agent = KameAgent(workspace=tmp_path, console=Console(file=StringIO()), auto_run_safe_commands=False)
    inspection = _inspection(tmp_path)
    prompts: list[str] = []

    def fake_confirm(prompt: str, *_args: Any, **_kwargs: Any) -> bool:
        prompts.append(prompt)
        return False

    monkeypatch.setattr("rich.prompt.Confirm.ask", fake_confirm)

    results = agent._handle_commands(inspection, ["python -m pytest"])

    assert results == []
    assert prompts == ["Run command: python -m pytest"]


def _inspection(workspace: Path) -> ProjectInspection:
    return ProjectInspection(
        workspace=workspace,
        files=[],
        config_files=[],
        detected_project_type="unknown",
        package_manager=None,
        test_commands=[],
    )


def _proposal(
    summary: str = "Task turn",
    commands: list[str] | None = None,
    changes: list[PlannedChange] | None = None,
) -> ChangeProposal:
    return ChangeProposal(
        summary=summary,
        reasoning_summary="Reason",
        detected_project_type="unknown",
        files_read=[],
        commands_to_run=commands or [],
        changes=changes or [],
    )
