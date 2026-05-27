# Author: kamekingdom (2026-05-27)

from __future__ import annotations

from io import StringIO
from pathlib import Path

from rich.console import Console

from kame_agent.agent import KameAgent
from kame_agent.models import ChangeProposal, CommandResult, PlannedChange, ProjectInspection


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


def _inspection(workspace: Path) -> ProjectInspection:
    return ProjectInspection(
        workspace=workspace,
        files=[],
        config_files=[],
        detected_project_type="unknown",
        package_manager=None,
        test_commands=[],
    )
