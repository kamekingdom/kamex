# Author: kamekingdom (2026-05-27)

from __future__ import annotations

from pathlib import Path

from kame_agent.scanner import inspect_workspace, is_task_relevant_file, task_keywords


def test_task_keywords_extracts_japanese_create_python_game_terms() -> None:
    terms = task_keywords("このディレクトリにじゃんけんゲームをするpythonプロジェクトを作成してください")

    assert "create" in terms
    assert "python" in terms
    assert "game" in terms


def test_task_relevant_file_matches_prompt_terms() -> None:
    terms = task_keywords("READMEを更新して")

    assert is_task_relevant_file("README.md", terms)
    assert not is_task_relevant_file("unrelated.log", terms)


def test_inspect_workspace_includes_files_under_current_workspace(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("notes\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")

    inspection = inspect_workspace(tmp_path, "このディレクトリの実装を確認して")

    assert "README.md" in inspection.files
    assert "notes.txt" in inspection.files
    assert "src/app.py" in inspection.files


def test_inspect_workspace_prioritizes_relevant_files_and_configs(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "random.css").write_text("body {}\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")

    inspection = inspect_workspace(tmp_path, "pythonを確認して")

    assert inspection.files.index("pyproject.toml") < inspection.files.index("random.css")
    assert inspection.files.index("src/app.py") < inspection.files.index("random.css")


def test_inspect_workspace_excludes_secret_files_in_subdirectories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / ".env").write_text("OPENAI_API_KEY=x\n", encoding="utf-8")
    (tmp_path / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")

    inspection = inspect_workspace(tmp_path, "このディレクトリを確認して")

    assert "src/app.py" in inspection.files
    assert "src/.env" not in inspection.files
