# Author: kamekingdom (2026-06-10)

from __future__ import annotations

from kame_agent.context import extract_file_mentions


def test_extract_file_mentions_deduplicates_and_strips_punctuation() -> None:
    text = "Update @src/app.py, compare @tests/test_app.py and @src/app.py."

    assert extract_file_mentions(text) == ["src/app.py", "tests/test_app.py"]


def test_extract_file_mentions_supports_windows_like_paths() -> None:
    assert extract_file_mentions(r"Check @src\\app.py") == ["src/app.py"]
