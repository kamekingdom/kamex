# Author: kamekingdom (2026-05-27)

from __future__ import annotations

from kame_agent.llm import extract_web_sources, parse_reading_plan


def test_parse_reading_plan_supports_web_search_queries() -> None:
    plan = parse_reading_plan(
        {
            "files_to_read": ["README.md"],
            "web_search_queries": ["latest pytest unittest discovery"],
            "notes": ["Need current docs."],
        }
    )

    assert plan.files_to_read == ["README.md"]
    assert plan.web_search_queries == ["latest pytest unittest discovery"]
    assert plan.notes == ["Need current docs."]


def test_parse_reading_plan_defaults_web_search_queries() -> None:
    plan = parse_reading_plan({"files_to_read": []})

    assert plan.web_search_queries == []


def test_extract_web_sources_from_response_dict() -> None:
    response = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "annotations": [
                            {"type": "url_citation", "url": "https://example.test/a"},
                            {"type": "url_citation", "url": "https://example.test/a"},
                            {"type": "url_citation", "url": "https://example.test/b"},
                        ]
                    }
                ],
            }
        ]
    }

    assert extract_web_sources(response) == ["https://example.test/a", "https://example.test/b"]
