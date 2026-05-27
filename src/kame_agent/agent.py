# Author: kamekingdom (2026-05-27)

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from kame_agent.commands import run_user_approved_command
from kame_agent.config import AppConfig, load_config, save_openai_api_key
from kame_agent.diffing import generate_diff
from kame_agent.exceptions import KameAgentError, SafetyError
from kame_agent.fs import apply_changes, read_text_file, validate_change
from kame_agent.llm import OpenAIModelClient
from kame_agent.models import (
    ChangeProposal,
    CommandResult,
    ProjectInspection,
    TokenUsage,
    UsageCost,
    UsageTotals,
    WebSearchResult,
)
from kame_agent.safety import command_permission_label, validate_user_approved_command
from kame_agent.scanner import inspect_workspace
from kame_agent.usage import append_usage_history, estimate_usage_cost, read_usage_totals


class KameAgent:
    def __init__(
        self,
        workspace: Path,
        console: Console | None = None,
        model_override: str | None = None,
        web_search_enabled: bool = True,
    ) -> None:
        self.workspace = workspace
        self.console = console or Console()
        self.model_override = model_override
        self.web_search_enabled = web_search_enabled

    def run_task(self, task: str) -> int:
        try:
            config = self._ensure_config(self.workspace)
            self.console.print("[bold cyan][Agent][/bold cyan] Inspecting project...")
            inspection = inspect_workspace(self.workspace, task)
            self._print_inspection(inspection)

            client = OpenAIModelClient(config)

            self.console.print("[bold cyan][Agent][/bold cyan] Planning files and web searches...")
            reading_plan = client.create_reading_plan(task, inspection)
            if reading_plan.notes:
                self.console.print(Panel(Text("\n".join(reading_plan.notes)), title="Reading Plan", border_style="blue"))

            self.console.print("[bold cyan][Agent][/bold cyan] Reading selected files...")
            file_context = self._read_files(inspection, reading_plan.files_to_read)
            web_context = self._perform_web_searches(client, reading_plan.web_search_queries)

            self.console.print("[bold cyan][Agent][/bold cyan] Generating change proposal...")
            proposal = client.create_change_proposal(task, inspection, file_context, web_context)
            proposal = self._sanitize_proposal(inspection, proposal)
            self._print_proposal(proposal)

            self.console.print("[bold cyan][Agent][/bold cyan] Generating diff...")
            diff = generate_diff(inspection.workspace, proposal.changes)
            if not diff.strip():
                self.console.print("[yellow]No file changes were proposed.[/yellow]")
            else:
                self.console.print(Panel(Text(diff), title="Diff", border_style="yellow"))

            if proposal.changes and Confirm.ask("Apply these changes?", default=False):
                apply_changes(inspection.workspace, proposal.changes)
                self.console.print("[green]Changes applied.[/green]")
            else:
                self.console.print("[yellow]No changes were applied.[/yellow]")

            self._handle_commands(inspection, proposal.commands_to_run)
            self._print_summary(proposal, client.token_usage, config.model)
            return 0
        except KameAgentError as exc:
            self.console.print(f"[bold red]Error:[/bold red] {exc}")
            return 1

    def _read_files(self, inspection: ProjectInspection, files_to_read: list[str]) -> dict[str, str]:
        context: dict[str, str] = {}
        read_table = Table(title="Files Read")
        read_table.add_column("Path")
        for path in files_to_read:
            try:
                snapshot = read_text_file(inspection.workspace, path)
            except SafetyError as exc:
                self.console.print(f"[yellow]Skipping unsafe file:[/yellow] {path} ({exc})")
                continue
            context[snapshot.path] = snapshot.content
            read_table.add_row(Text(snapshot.path))
        self.console.print(read_table)
        return context

    def _perform_web_searches(self, client: OpenAIModelClient, queries: list[str]) -> list[WebSearchResult]:
        if not queries:
            return []
        if not self.web_search_enabled:
            self.console.print("[yellow]Web search was requested by the model but is disabled.[/yellow]")
            return []
        table = Table(title="Proposed Web Searches")
        table.add_column("Query")
        for query in queries:
            table.add_row(Text(query))
        self.console.print(table)
        if not Confirm.ask("Allow OpenAI API web search for these queries?", default=False):
            self.console.print("[yellow]Web search skipped.[/yellow]")
            return []
        results: list[WebSearchResult] = []
        for query in queries:
            self.console.print("[bold cyan][Agent][/bold cyan] Web searching ", Text(query))
            try:
                result = client.perform_web_search(query)
            except KameAgentError as exc:
                self.console.print(f"[yellow]Web search failed:[/yellow] {exc}")
                continue
            results.append(result)
        self._print_web_search_results(results)
        return results

    def _print_web_search_results(self, results: list[WebSearchResult]) -> None:
        if not results:
            return
        lines: list[str] = []
        for result in results:
            lines.append(f"Query: {result.query}")
            lines.append(result.summary)
            if result.sources:
                lines.append("Sources:")
                lines.extend(f"- {source}" for source in result.sources)
            lines.append("")
        self.console.print(Panel(Text("\n".join(lines).strip()), title="Web Search Results", border_style="blue"))

    def _sanitize_proposal(self, inspection: ProjectInspection, proposal: ChangeProposal) -> ChangeProposal:
        for change in proposal.changes:
            validate_change(inspection.workspace, change)
        safe_commands: list[str] = []
        notes = list(proposal.notes)
        for command in proposal.commands_to_run:
            try:
                validate_user_approved_command(command)
            except SafetyError as exc:
                notes.append(f"Skipped invalid command: {command} ({exc})")
                continue
            permission = command_permission_label(command)
            if permission != "inspection allowlist":
                notes.append(f"Command requires {permission} before running: {command}")
            safe_commands.append(command)
        return ChangeProposal(
            summary=proposal.summary,
            reasoning_summary=proposal.reasoning_summary,
            detected_project_type=proposal.detected_project_type,
            files_read=proposal.files_read,
            commands_to_run=safe_commands,
            changes=proposal.changes,
            notes=notes,
        )

    def _ensure_config(self, workspace: Path) -> AppConfig:
        config = load_config(workspace, self.model_override)
        if config.api_key:
            return config
        self.console.print("[yellow]OPENAI_API_KEY is not set.[/yellow]")
        api_key = Prompt.ask("Enter OPENAI_API_KEY", password=True).strip()
        if not api_key:
            raise KameAgentError("OPENAI_API_KEY was not provided.")
        saved_path = save_openai_api_key(api_key)
        self.console.print(f"[green]Saved OPENAI_API_KEY for future runs:[/green] {saved_path}")
        return load_config(workspace, self.model_override)

    def _handle_commands(self, inspection: ProjectInspection, commands: list[str]) -> None:
        if not commands:
            return
        command_table = Table(title="Proposed Commands")
        command_table.add_column("Command")
        command_table.add_column("Permission")
        for command in commands:
            permission = command_permission_label(command)
            command_table.add_row(Text(command), Text(permission))
        self.console.print(command_table)
        for command in commands:
            escaped_command = escape(command)
            prompt = f"Run command: {escaped_command}"
            permission = command_permission_label(command)
            if permission == "high-risk one-time approval":
                prompt = f"Grant HIGH-RISK one-time permission and run command: {escaped_command}"
            elif permission != "inspection allowlist":
                prompt = f"Grant one-time permission and run command: {escaped_command}"
            if Confirm.ask(prompt, default=False):
                self.console.print("[bold cyan][Agent][/bold cyan] Running ", Text(command))
                result = run_user_approved_command(inspection.workspace, command)
                self._print_command_result(result)

    def _print_inspection(self, inspection: ProjectInspection) -> None:
        table = Table(title="Project")
        table.add_column("Item")
        table.add_column("Value")
        table.add_row("Workspace", Text(str(inspection.workspace)))
        table.add_row("Detected type", Text(inspection.detected_project_type))
        table.add_row("Package manager", Text(inspection.package_manager or "unknown"))
        table.add_row("Files found", str(len(inspection.files)))
        table.add_row("Config files", Text(", ".join(inspection.config_files) or "-"))
        table.add_row("Suggested tests", Text(", ".join(inspection.test_commands) or "-"))
        self.console.print(table)
        files_to_show = inspection.files[:120]
        remainder = len(inspection.files) - len(files_to_show)
        file_body = "\n".join(files_to_show) if files_to_show else "No readable project files found."
        if remainder > 0:
            file_body += f"\n... {remainder} more files"
        self.console.print(Panel(Text(file_body), title="Inspected Files", border_style="cyan"))
        if inspection.git_status:
            self.console.print(Panel(Text(inspection.git_status), title="Git Status", border_style="blue"))

    def _print_proposal(self, proposal: ChangeProposal) -> None:
        table = Table(title="Proposal")
        table.add_column("Item")
        table.add_column("Value")
        table.add_row("Summary", Text(proposal.summary))
        table.add_row("Reason", Text(proposal.reasoning_summary))
        table.add_row("Detected type", Text(proposal.detected_project_type))
        table.add_row("Files read", Text(", ".join(proposal.files_read) or "-"))
        table.add_row("Changes", Text(", ".join(change.path for change in proposal.changes) or "-"))
        table.add_row("Commands", Text(", ".join(proposal.commands_to_run) or "-"))
        self.console.print(table)
        if proposal.notes:
            self.console.print(Panel(Text("\n".join(proposal.notes)), title="Notes", border_style="magenta"))

    def _print_command_result(self, result: CommandResult) -> None:
        body = f"exit code: {result.returncode}\n"
        if result.stdout:
            body += f"\nSTDOUT:\n{result.stdout}"
        if result.stderr:
            body += f"\nSTDERR:\n{result.stderr}"
        style = "green" if result.returncode == 0 else "red"
        self.console.print(Panel(Text(body), title=Text(result.command), border_style=style))

    def _print_summary(self, proposal: ChangeProposal, token_usage: TokenUsage, model: str) -> None:
        lines = [proposal.summary or "Task completed."]
        if proposal.changes:
            lines.append("Changed files:")
            lines.extend(f"- {change.path}" for change in proposal.changes)
        self.console.print(Panel(Text("\n".join(lines)), title="Final Summary", border_style="green"))
        cost = estimate_usage_cost(model, token_usage)
        history_path = append_usage_history(model, token_usage, cost, self.workspace)
        totals = read_usage_totals(history_path)
        self._print_token_usage(token_usage, model, cost, totals, history_path)

    def _print_token_usage(
        self,
        token_usage: TokenUsage,
        model: str,
        cost: UsageCost,
        totals: UsageTotals,
        history_path: Path,
    ) -> None:
        table = Table(title="Token Usage")
        table.add_column("Item")
        table.add_column("Current", justify="right")
        table.add_column("All Time", justify="right")
        table.add_row("Model", model, "-")
        table.add_row("Runs", "1", str(totals.runs))
        table.add_row("Input tokens", str(token_usage.input_tokens), str(totals.input_tokens))
        table.add_row("Output tokens", str(token_usage.output_tokens), str(totals.output_tokens))
        table.add_row("Total tokens", str(token_usage.total_tokens), str(totals.total_tokens))
        table.add_row("Estimated cost", _format_cost(cost.total_cost_usd), _format_cost(totals.total_cost_usd))
        table.add_row("History", str(history_path), "-")
        self.console.print(table)


def _format_cost(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"${value:.6f}"
