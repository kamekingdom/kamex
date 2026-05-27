# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kame_agent.config import get_user_config_dir
from kame_agent.models import TokenUsage, UsageCost, UsageTotals

USAGE_HISTORY_FILE_NAME = "usage_history.jsonl"

# USD per 1M tokens. Override with:
# KAMEX_PRICE_<MODEL>_INPUT_PER_1M / KAMEX_PRICE_<MODEL>_OUTPUT_PER_1M
# where non-alphanumeric model chars become underscores and uppercase.
DEFAULT_PRICE_TABLE_USD_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-5.2": (1.25, 10.0),
    "gpt-5.1": (1.25, 10.0),
    "gpt-5": (1.25, 10.0),
    "gpt-4.1": (2.0, 8.0),
    "gpt-4.1-mini": (0.4, 1.6),
}


def usage_history_file() -> Path:
    return get_user_config_dir() / USAGE_HISTORY_FILE_NAME


def estimate_usage_cost(model: str, usage: TokenUsage) -> UsageCost:
    rates = price_rates_for_model(model)
    if rates is None:
        return UsageCost(input_cost_usd=None, output_cost_usd=None, total_cost_usd=None)
    input_rate, output_rate = rates
    input_cost = usage.input_tokens * input_rate / 1_000_000
    output_cost = usage.output_tokens * output_rate / 1_000_000
    return UsageCost(
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        total_cost_usd=input_cost + output_cost,
    )


def price_rates_for_model(model: str) -> tuple[float, float] | None:
    key = _model_env_key(model)
    input_override = os.environ.get(f"KAMEX_PRICE_{key}_INPUT_PER_1M")
    output_override = os.environ.get(f"KAMEX_PRICE_{key}_OUTPUT_PER_1M")
    if input_override and output_override:
        try:
            return float(input_override), float(output_override)
        except ValueError:
            return None
    for prefix, rates in DEFAULT_PRICE_TABLE_USD_PER_1M.items():
        if model == prefix or model.startswith(prefix + "-"):
            return rates
    return None


def append_usage_history(
    model: str,
    usage: TokenUsage,
    cost: UsageCost,
    workspace: Path,
) -> Path:
    path = usage_history_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "workspace": str(workspace),
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "input_cost_usd": cost.input_cost_usd,
        "output_cost_usd": cost.output_cost_usd,
        "total_cost_usd": cost.total_cost_usd,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def read_usage_totals(path: Path | None = None) -> UsageTotals:
    history_path = path or usage_history_file()
    if not history_path.exists():
        return UsageTotals(runs=0, input_tokens=0, output_tokens=0, total_tokens=0, total_cost_usd=0.0)
    runs = 0
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    total_cost = 0.0
    has_unknown_cost = False
    for line in history_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        runs += 1
        input_tokens += _int_value(record.get("input_tokens"))
        output_tokens += _int_value(record.get("output_tokens"))
        total_tokens += _int_value(record.get("total_tokens"))
        cost = record.get("total_cost_usd")
        if isinstance(cost, (int, float)):
            total_cost += float(cost)
        else:
            has_unknown_cost = True
    return UsageTotals(
        runs=runs,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        total_cost_usd=None if has_unknown_cost else total_cost,
    )


def _model_env_key(model: str) -> str:
    chars = [char.upper() if char.isalnum() else "_" for char in model]
    return "".join(chars).strip("_")


def _int_value(value: Any) -> int:
    return value if isinstance(value, int) else 0
