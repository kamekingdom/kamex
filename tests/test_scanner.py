# Author: kamekingdom (2026-05-27)

from __future__ import annotations

from pathlib import Path

from kame_agent.scanner import content_search_terms, inspect_workspace, is_task_relevant_file, task_keywords


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


def test_inspect_workspace_loads_agent_instruction_files(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("Run python -m pytest before finishing.\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "CLAUDE.md").write_text("Prefer small modules here.\n", encoding="utf-8")
    (tmp_path / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")

    inspection = inspect_workspace(tmp_path, "srcを修正して")

    assert "AGENTS.md" in inspection.files
    assert "src/CLAUDE.md" in inspection.files
    assert inspection.project_instructions == {
        "AGENTS.md": "Run python -m pytest before finishing.\n",
        "src/CLAUDE.md": "Prefer small modules here.\n",
    }


def test_inspect_workspace_adds_content_search_snippets(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "handlers.py").write_text(
        "def login_handler():\n    return authenticate_user()\n",
        encoding="utf-8",
    )
    (tmp_path / "style.css").write_text("body {}\n", encoding="utf-8")

    inspection = inspect_workspace(tmp_path, "login authenticate bug")

    assert any("src/handlers.py:1" in snippet and "login_handler" in snippet for snippet in inspection.search_snippets)
    assert inspection.files.index("src/handlers.py") < inspection.files.index("style.css")


def test_content_search_terms_removes_common_words() -> None:
    assert "please" not in content_search_terms("please fix login")
    assert "login" in content_search_terms("please fix login")
