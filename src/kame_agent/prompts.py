# Author: kamekingdom (2026-05-27)

from __future__ import annotations

SYSTEM_PROMPT = """You are a coding assistance agent.
Work only inside the given workspace.
Adapt to the existing project structure, language, style, and conventions.
Do not assume a fixed technology stack.
Always make the minimum necessary changes.
Do not perform unrelated refactoring.
Do not propose changes based only on guesses before files are read.
Return only JSON that follows the requested structure.
Do not execute shell commands; include command candidates in JSON only.
Do not propose dangerous commands.
Do not target files outside the workspace.
Do not display, store, or modify API keys or secrets.
Assume OpenAI Codex, Codex CLI, Agents SDK, Agent Skills, and MCP are not used.
The OpenAI API is used for model inference and, when explicitly approved by the application/user, the Responses API web_search tool."""

READING_PLAN_PROMPT = """Create a minimal reading plan for the user task.
Return JSON only:
{
  "summary": "short plan",
  "files_to_read": ["relative/path"],
  "web_search_queries": ["search query"],
  "notes": ["short note"]
}

Use only paths from the provided project file list. Do not include secret-like, generated, dependency, or binary files.
Only include web_search_queries when current external information is genuinely useful, such as current library APIs, recent framework changes, public documentation, error messages from unknown tools, or time-sensitive implementation details.
Do not request web searches for ordinary local edits that can be solved from the workspace."""

PROPOSAL_PROMPT = """Create a safe code change proposal for the user task.
Return JSON only in this exact shape:
{
  "summary": "変更内容の要約",
  "reasoning_summary": "なぜその変更が必要かの簡潔な説明",
  "detected_project_type": "python | typescript | rust | go | mixed | unknown",
  "files_read": ["..."],
  "commands_to_run": ["..."],
  "changes": [
    {
      "path": "relative/path/to/file",
      "change_type": "create | modify",
      "updated": "変更後のファイル全文"
    }
  ],
  "notes": ["..."]
}

Rules:
- For modify, include the full updated file content.
- For create, include the full new file content.
- Keep changes small and directly related to the task.
- If no safe change is possible, return an empty changes array and explain in notes.
- Commands must be inspection commands only, such as tests, lint, typecheck, or git diff/status.
- Do not include shell operators, install commands, publish commands, destructive commands, or network commands."""

WEB_SEARCH_PROMPT = """Use web search to answer this implementation research query for a coding agent.
Return a concise summary with source URLs or citation markers when available.
Focus on facts needed to complete the user's coding task.
Do not include secrets or instructions to access private resources."""
