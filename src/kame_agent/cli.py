# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from kame_agent import __version__
from kame_agent.agent import KameAgent
from kame_agent.commands import run_user_approved_command
from kame_agent.config import load_config
from kame_agent.session_log import latest_task, read_session_events, workspace_session_file
from kame_agent.update import UpdateInfo, check_for_update


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kamex",
        description="OpenAI API based CLI coding agent.",
    )
    parser.add_argument("instruction", nargs="*", help="Natural language task to run.")
    parser.add_argument("--workspace", "-w", help="Target workspace directory. Defaults to the current directory.")
    parser.add_argument("--model", help="Temporarily override the OpenAI model for this run.")
    parser.add_argument("--no-web-search", action="store_true", help="Disable optional OpenAI API web search.")
    parser.add_argument(
        "--no-auto-run-safe-commands",
        action="store_true",
        help="Ask before running allowlisted local verification commands.",
    )
    parser.add_argument(
        "--no-review",
        action="store_true",
        help="Disable the extra model review pass before showing a proposal.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=5,
        help="Maximum agent turns for one task before returning to the prompt.",
    )
    parser.add_argument(
        "--max-context-rounds",
        type=int,
        default=2,
        help="Maximum extra file-discovery rounds after the initial reading plan.",
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    console = Console()
    if args.version or _is_version_command(args.instruction):
        console.print(f"kamex {__version__}")
        return 0
    workspace = resolve_cli_workspace(args.workspace)
    if _is_update_command(args.instruction):
        maybe_offer_update(console, workspace)
        return 0
    if _is_history_command(args.instruction):
        print_history(console, workspace)
        return 0
    instruction = " ".join(args.instruction).strip()
    if _is_resume_command(args.instruction):
        task = latest_task(workspace)
        if task is None:
            console.print("[yellow]No previous task found for this workspace.[/yellow]")
            return 0
        instruction = build_resume_instruction(task)
    model = load_config(workspace, args.model).model
    _print_banner(console, workspace, model)
    agent = KameAgent(
        workspace=workspace,
        console=console,
        model_override=args.model,
        web_search_enabled=not args.no_web_search,
        max_task_turns=args.max_turns,
        auto_run_safe_commands=not args.no_auto_run_safe_commands,
        review_proposals=not args.no_review,
        max_context_expansion_rounds=args.max_context_rounds,
    )
    if instruction:
        return agent.run_task(instruction)
    return _interactive_loop(agent, console)


def _interactive_loop(agent: KameAgent, console: Console) -> int:
    while True:
        try:
            instruction = Prompt.ask("\n[bold]>[/bold]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Bye.[/yellow]")
            return 0
        if instruction.lower() in {"exit", "quit", ":q"}:
            return 0
        if not instruction:
            continue
        code = agent.run_task(instruction)
        if code != 0:
            return code


def _print_banner(console: Console, workspace: Path, model: str | None = None) -> None:
    banner = "kamex\nOpenAI API based CLI agent"
    console.print(Panel(banner, border_style="cyan"))
    console.print(f"Project: {workspace.resolve()}")
    if model:
        console.print(f"Model: {model}")


def _is_version_command(instruction: list[str]) -> bool:
    return len(instruction) == 1 and instruction[0].lower() == "version"


def _is_update_command(instruction: list[str]) -> bool:
    return len(instruction) == 1 and instruction[0].lower() == "update"


def _is_history_command(instruction: list[str]) -> bool:
    return len(instruction) == 1 and instruction[0].lower() == "history"


def _is_resume_command(instruction: list[str]) -> bool:
    return len(instruction) == 1 and instruction[0].lower() == "resume"


def resolve_cli_workspace(workspace_arg: str | None) -> Path:
    if workspace_arg is None:
        return Path.cwd()
    return Path(workspace_arg).expanduser()


def print_history(console: Console, workspace: Path) -> None:
    events = read_session_events(workspace)
    completed = [event for event in events if event.get("event_type") == "task_completed"]
    table = Table(title="kamex history")
    table.add_column("Time")
    table.add_column("Task")
    table.add_column("Turns", justify="right")
    table.add_column("Changed files")
    for event in completed[-10:]:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        changed = payload.get("changed_files")
        changed_text = ", ".join(changed) if isinstance(changed, list) else "-"
        table.add_row(
            str(event.get("created_at", "-")),
            str(payload.get("task", "-")),
            str(payload.get("turns", "-")),
            changed_text or "-",
        )
    console.print(table)
    console.print(f"Session log: {workspace_session_file(workspace)}")


def build_resume_instruction(task: str) -> str:
    return (
        "Resume the most recent kamex task for this workspace.\n\n"
        f"Previous task:\n{task}\n\n"
        "Use the current workspace files, project instructions, workspace memory, "
        "and session log context. Continue only if there is remaining useful work; "
        "otherwise inspect and return no changes with a concise completion summary."
    )


def maybe_offer_update(console: Console, workspace: Path) -> None:
    info = check_for_update(__version__)
    if info is None:
        return
    _print_update_info(console, info)
    if not Confirm.ask("Update kamex now?", default=False):
        return
    result = run_user_approved_command(workspace, info.install_command, timeout_seconds=300)
    body = f"exit code: {result.returncode}\n"
    if result.stdout:
        body += f"\nSTDOUT:\n{result.stdout}"
    if result.stderr:
        body += f"\nSTDERR:\n{result.stderr}"
    style = "green" if result.returncode == 0 else "red"
    console.print(Panel(Text(body), title=Text("kamex update"), border_style=style))


def _print_update_info(console: Console, info: UpdateInfo) -> None:
    body = (
        f"Current: {info.current_version}\n"
        f"Latest:  {info.latest_version}\n"
        f"Source:  {info.source_url}\n"
        f"Command: {info.install_command}"
    )
    console.print(Panel(Text(body), title="Update Available", border_style="yellow"))
