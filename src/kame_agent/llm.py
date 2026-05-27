# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import json
from typing import Any, cast

from openai import OpenAI, OpenAIError

from kame_agent.config import AppConfig
from kame_agent.exceptions import LLMError, ProposalError
from kame_agent.models import ChangeProposal, PlannedChange, ProjectInspection, ProjectType, ReadingPlan, WebSearchResult
from kame_agent.prompts import PROPOSAL_PROMPT, READING_PLAN_PROMPT, SYSTEM_PROMPT, WEB_SEARCH_PROMPT


class OpenAIModelClient:
    def __init__(self, config: AppConfig) -> None:
        if not config.api_key:
            raise LLMError("OPENAI_API_KEY is not set.")
        self._client = OpenAI(api_key=config.api_key)
        self._model = config.model

    def create_reading_plan(self, task: str, inspection: ProjectInspection) -> ReadingPlan:
        payload = {
            "task": task,
            "workspace": str(inspection.workspace),
            "detected_project_type": inspection.detected_project_type,
            "package_manager": inspection.package_manager,
            "test_commands": inspection.test_commands,
            "config_files": inspection.config_files,
            "files": inspection.files,
            "git_status": inspection.git_status,
            "git_diff": inspection.git_diff,
        }
        data = self._request_json(READING_PLAN_PROMPT, payload)
        plan = parse_reading_plan(data)
        if not all(path in inspection.files for path in plan.files_to_read):
            unknown = [path for path in plan.files_to_read if path not in inspection.files]
            raise ProposalError(f"Reading plan included unknown files: {', '.join(unknown)}")
        return plan

    def perform_web_search(self, query: str) -> WebSearchResult:
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=SYSTEM_PROMPT,
                tools=[{"type": "web_search"}],
                include=["web_search_call.action.sources"],
                input=f"{WEB_SEARCH_PROMPT}\n\nQUERY:\n{query}",
            )
        except OpenAIError as exc:
            raise LLMError(f"OpenAI API web search failed: {exc}") from exc
        output = getattr(response, "output_text", "")
        if not isinstance(output, str) or not output.strip():
            raise LLMError("OpenAI API web search response did not contain output_text.")
        return WebSearchResult(query=query, summary=output.strip(), sources=extract_web_sources(response))

    def create_change_proposal(
        self,
        task: str,
        inspection: ProjectInspection,
        file_context: dict[str, str],
        web_context: list[WebSearchResult] | None = None,
    ) -> ChangeProposal:
        web_results = web_context or []
        payload = {
            "task": task,
            "inspection": {
                "workspace": str(inspection.workspace),
                "detected_project_type": inspection.detected_project_type,
                "package_manager": inspection.package_manager,
                "test_commands": inspection.test_commands,
                "config_files": inspection.config_files,
                "files": inspection.files,
                "git_status": inspection.git_status,
                "git_diff": inspection.git_diff,
            },
            "files": file_context,
            "web_search_results": [
                {"query": result.query, "summary": result.summary, "sources": result.sources}
                for result in web_results
            ],
        }
        data = self._request_json(PROPOSAL_PROMPT, payload)
        return parse_change_proposal(data)

    def _request_json(self, prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=SYSTEM_PROMPT,
                input=f"{prompt}\n\nINPUT_JSON:\n{json.dumps(payload, ensure_ascii=False)}",
            )
        except OpenAIError as exc:
            raise LLMError(f"OpenAI API request failed: {exc}") from exc
        output = getattr(response, "output_text", "")
        if not isinstance(output, str) or not output.strip():
            raise LLMError("OpenAI API response did not contain output_text.")
        return parse_json_object(output)


def parse_reading_plan(data: dict[str, Any]) -> ReadingPlan:
    files = data.get("files_to_read", [])
    if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
        raise ProposalError("Reading plan did not contain a valid files_to_read array.")
    queries = data.get("web_search_queries", [])
    if not isinstance(queries, list) or not all(isinstance(item, str) for item in queries):
        raise ProposalError("Reading plan did not contain a valid web_search_queries array.")
    notes = data.get("notes", [])
    if not isinstance(notes, list):
        notes = []
    return ReadingPlan(
        files_to_read=files,
        web_search_queries=_bounded_string_list(queries, max_items=5, max_length=200),
        notes=_string_list(notes),
    )


def _bounded_string_list(value: list[str], max_items: int, max_length: int) -> list[str]:
    items: list[str] = []
    for item in value[:max_items]:
        cleaned = item.strip()
        if cleaned:
            items.append(cleaned[:max_length])
    return items


def extract_web_sources(response: Any) -> list[str]:
    data = _response_to_dict(response)
    sources: list[str] = []
    for item in _walk_values(data):
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if isinstance(url, str) and url not in sources:
            sources.append(url)
    return sources[:20]


def _response_to_dict(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        dumped = response.model_dump()
        if isinstance(dumped, dict):
            return dumped
    if isinstance(response, dict):
        return response
    return {}


def _walk_values(value: Any) -> list[Any]:
    values = [value]
    if isinstance(value, dict):
        for child in value.values():
            values.extend(_walk_values(child))
    elif isinstance(value, list):
        for child in value:
            values.extend(_walk_values(child))
    return values


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise LLMError("Model output was not a JSON object.")
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError(f"Model output JSON could not be parsed: {exc}") from exc
    if not isinstance(parsed, dict):
        raise LLMError("Model output JSON was not an object.")
    return parsed


def parse_change_proposal(data: dict[str, Any]) -> ChangeProposal:
    changes_raw = data.get("changes", [])
    if not isinstance(changes_raw, list):
        raise ProposalError("changes must be an array.")
    changes: list[PlannedChange] = []
    for item in changes_raw:
        if not isinstance(item, dict):
            raise ProposalError("Each change must be an object.")
        path = item.get("path")
        change_type = item.get("change_type")
        updated = item.get("updated")
        if not isinstance(path, str) or change_type not in ("create", "modify") or not isinstance(updated, str):
            raise ProposalError("Each change requires path, change_type, and updated fields.")
        changes.append(PlannedChange(path=path, change_type=change_type, updated=updated))
    return ChangeProposal(
        summary=str(data.get("summary", "")),
        reasoning_summary=str(data.get("reasoning_summary", "")),
        detected_project_type=_project_type(data.get("detected_project_type")),
        files_read=_string_list(data.get("files_read", [])),
        commands_to_run=_string_list(data.get("commands_to_run", [])),
        changes=changes,
        notes=_string_list(data.get("notes", [])),
    )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _project_type(value: Any) -> ProjectType:
    if value in ("python", "typescript", "rust", "go", "mixed", "unknown"):
        return cast(ProjectType, value)
    return "unknown"
