"""Artifact-level tests for MCP capability config files."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "app" / "mcp" / "default_capabilities.json"
EXAMPLE_CONFIG = ROOT / "app" / "mcp" / "example_capabilities.yaml"


def test_default_capability_config_contains_required_sections() -> None:
    payload = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))

    assert set(payload.keys()) == {"server", "tools", "resources", "prompts"}
    assert len(payload["tools"]) >= 3
    assert len(payload["resources"]) >= 1
    assert len(payload["prompts"]) >= 1


def test_default_capability_config_includes_templated_resource() -> None:
    payload = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    resource_map = {item["name"]: item for item in payload["resources"]}

    assert resource_map["market.quote"]["uriTemplate"] == "market://quote/{symbol}"


def test_default_capability_config_includes_apps_examples() -> None:
    payload = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    names = {item["name"] for item in payload["tools"]}

    assert "portfolio_get_summary" in names
    assert "portfolio_get_period_inputs" in names
    assert "holdings_open_create_form" in names
    assert "portfolio_rebalance_workflow" in names
    assert "overview_get_dashboard" in names
    assert "onboarding_open_manual_form" in names


def test_period_inputs_are_interpreter_facts_without_app_ui() -> None:
    payload = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    tool_map = {item["name"]: item for item in payload["tools"]}

    period_tool = tool_map["portfolio_get_period_inputs"]
    assert period_tool["handler"] == "tool_portfolio_get_period_inputs"
    assert period_tool["inputSchema"]["required"] == ["start_date", "end_date"]
    assert "meta" not in period_tool


def test_default_capability_config_keeps_prompt_completion_inputs() -> None:
    payload = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    prompt_map = {item["name"]: item for item in payload["prompts"]}

    summary_prompt = prompt_map["portfolio.analysis.summary"]
    argument_names = {argument["name"] for argument in summary_prompt["arguments"]}
    assert "currency" in argument_names


def test_example_yaml_exists() -> None:
    assert EXAMPLE_CONFIG.exists()
