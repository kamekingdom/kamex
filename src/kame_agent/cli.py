# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from kame_agent import __version__
from kame_agent.agent import KameAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kamex",
        description="OpenAI API based CLI coding agent.",
    )
    parser.add_argument("instruction", nargs="*", help="Natural language task to run once.")
    parser.add_argument("--workspace", "-w", help="Target workspace directory. Defaults to the current directory.")
    parser.add_argument("--model", help="Temporarily override the OpenAI model for this run.")
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
    _print_banner(console, workspace)
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


def _print_banner(console: Console, workspace: Path) -> None:
    banner = "kamex\nOpenAI API based CLI agent"
    console.print(Panel(banner, border_style="cyan"))
    console.print(f"Project: {workspace.resolve()}")


def _is_version_command(instruction: list[str]) -> bool:
    return len(instruction) == 1 and instruction[0].lower() == "version"


def resolve_cli_workspace(workspace_arg: str | None) -> Path:
    if workspace_arg is None:
        return Path.cwd()
    return Path(workspace_arg).expanduser()
