# Author: kamekingdom (2026-05-27)

from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from kame_agent.models import TokenUsage
from kame_agent.usage import (
    append_usage_history,
    estimate_usage_cost,
    price_rates_for_model,
    read_usage_totals,
    usage_history_file,
)


def test_estimate_usage_cost_known_model() -> None:
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=500_000, total_tokens=1_500_000)

    cost = estimate_usage_cost("gpt-5.2", usage)

    assert cost.input_cost_usd == 1.25
    assert cost.output_cost_usd == 5.0
    assert cost.total_cost_usd == 6.25


def test_estimate_usage_cost_unknown_model() -> None:
    cost = estimate_usage_cost("unknown-model", TokenUsage(total_tokens=10))

    assert cost.total_cost_usd is None


def test_price_rates_can_be_overridden(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("KAMEX_PRICE_MY_MODEL_INPUT_PER_1M", "3")
    monkeypatch.setenv("KAMEX_PRICE_MY_MODEL_OUTPUT_PER_1M", "9")

    assert price_rates_for_model("my-model") == (3.0, 9.0)


def test_append_usage_history_and_totals(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("KAMEX_CONFIG_DIR", str(tmp_path / "config"))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    usage = TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150)
    cost = estimate_usage_cost("gpt-5.2", usage)

    history_path = append_usage_history("gpt-5.2", usage, cost, workspace)
    append_usage_history("gpt-5.2", usage, cost, workspace)
    totals = read_usage_totals(history_path)

    assert history_path == usage_history_file()
    assert totals.runs == 2
    assert totals.input_tokens == 200
    assert totals.output_tokens == 100
    assert totals.total_tokens == 300
    assert totals.total_cost_usd is not None
