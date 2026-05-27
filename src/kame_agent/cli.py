# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.prompt import Prompt
from rich.text import Text

from kame_agent import __version__
from kame_agent.agent import KameAgent
from kame_agent.commands import run_user_approved_command
from kame_agent.config import load_config
from kame_agent.update import UpdateInfo, check_for_update


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kamex",
        description="OpenAI API based CLI coding agent.",
    )
    parser.add_argument("instruction", nargs="*", help="Natural language task to run once.")
    parser.add_argument("--workspace", "-w", help="Target workspace directory. Defaults to the current directory.")
    parser.add_argument("--model", help="Temporarily override the OpenAI model for this run.")
    parser.add_argument("--no-update-check", action="store_true", help="Skip GitHub update check on startup.")
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
    instruction = " ".join(args.instruction).strip()
    interactive = not instruction
    if not args.no_update_check:
        maybe_offer_update(console, workspace)
    model = load_config(workspace, args.model).model if interactive else None
    _print_banner(console, workspace, model)
    agent = KameAgent(workspace=workspace, console=console, model_override=args.model)
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


def resolve_cli_workspace(workspace_arg: str | None) -> Path:
    if workspace_arg is None:
        return Path.cwd()
    return Path(workspace_arg).expanduser()


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
