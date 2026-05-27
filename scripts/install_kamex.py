# Author: kamekingdom (2026-05-27)

from __future__ import annotations

import argparse
import os
import shutil
import site
import subprocess
import sys
import sysconfig
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install the kamex command from a cloned repository.")
    parser.add_argument("--dev", action="store_true", help="Install development extras.")
    parser.add_argument("--no-user", action="store_true", help="Install into the active environment instead of --user.")
    parser.add_argument("--dry-run", action="store_true", help="Print the pip command without running it.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = find_repo_root(Path(__file__).resolve())
    install_target = f"{repo_root}[dev]" if args.dev else str(repo_root)
    command = build_pip_install_command(install_target, use_user=should_use_user_install(args.no_user))
    print("Installing kamex command...")
    print(format_command(command))
    if args.dry_run:
        print_install_hint()
        return 0
    completed = subprocess.run(command, text=True, check=False)
    if completed.returncode != 0:
        print("Install failed.")
        return completed.returncode
    print("Install complete.")
    verify_command()
    print_install_hint()
    return 0


def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "src" / "kame_agent").is_dir():
            return candidate
    raise RuntimeError("Could not find kamex repository root.")


def build_pip_install_command(install_target: str, use_user: bool) -> list[str]:
    command = [sys.executable, "-m", "pip", "install", "-e", install_target]
    if use_user:
        command.insert(4, "--user")
    return command


def should_use_user_install(no_user: bool) -> bool:
    if no_user or is_virtualenv():
        return False
    return True


def is_virtualenv() -> bool:
    return sys.prefix != sys.base_prefix


def command_script_dir() -> Path:
    if is_virtualenv():
        return Path(sysconfig.get_path("scripts"))
    user_base = site.getuserbase()
    if os.name == "nt":
        return Path(user_base) / "Scripts"
    return Path(user_base) / "bin"


def verify_command() -> None:
    resolved = shutil.which("kamex")
    if resolved:
        print(f"kamex is available: {resolved}")
        subprocess.run(["kamex", "--version"], text=True, check=False)
        return
    script_dir = command_script_dir()
    suffix = ".exe" if os.name == "nt" else ""
    candidate = script_dir / f"kamex{suffix}"
    if candidate.exists():
        print(f"kamex was installed here: {candidate}")
    else:
        print("kamex command was installed, but its script path could not be confirmed.")


def print_install_hint() -> None:
    script_dir = command_script_dir()
    if _path_contains(script_dir):
        return
    print("")
    print("Add this directory to PATH if the kamex command is not found:")
    print(str(script_dir))
    if os.name == "nt":
        print('PowerShell example: $env:Path += ";' + str(script_dir) + '"')
    else:
        print(f'Unix shell example: export PATH="{script_dir}:$PATH"')


def format_command(command: list[str]) -> str:
    return " ".join(_quote(part) for part in command)


def _quote(value: str) -> str:
    if not value or any(char.isspace() for char in value):
        return '"' + value.replace('"', '\\"') + '"'
    return value


def _path_contains(path: Path) -> bool:
    target = str(path.resolve()).lower() if os.name == "nt" else str(path.resolve())
    for raw_part in os.environ.get("PATH", "").split(os.pathsep):
        if not raw_part:
            continue
        try:
            current = str(Path(raw_part).resolve())
        except OSError:
            current = raw_part
        current_key = current.lower() if os.name == "nt" else current
        if current_key == target:
            return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
