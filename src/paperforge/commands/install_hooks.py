"""paperforge install-hooks command — installs git pre-commit hook."""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()

HOOK_CONTENT = """#!/bin/sh
# PaperForge pre-commit hook
# Installed by: paperforge install-hooks
# Remove with:  paperforge install-hooks --uninstall

# Find paperforge on PATH or in current venv
if command -v paperforge >/dev/null 2>&1; then
    PAPERFORGE=paperforge
elif [ -f ".venv/bin/paperforge" ]; then
    PAPERFORGE=".venv/bin/paperforge"
elif [ -f ".venv/Scripts/paperforge.exe" ]; then
    PAPERFORGE=".venv/Scripts/paperforge.exe"
else
    echo "PaperForge: paperforge not found on PATH or in .venv/"
    echo "Skipping paper consistency check."
    exit 0
fi

# Only run if .paperforge/ exists in current directory
if [ ! -d ".paperforge" ]; then
    exit 0
fi

echo "PaperForge: running doctor checks..."
$PAPERFORGE doctor
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "PaperForge: commit blocked — fix ERRORs before committing."
    echo "Run 'paperforge doctor' to see all issues."
    echo "Run 'paperforge doctor --fix' to auto-resolve warnings."
    exit 1
fi

exit 0
"""


def _find_git_root(start: Path) -> Path | None:
    current = start
    while True:
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def run(project_root: Path, uninstall: bool = False) -> None:
    """Install or uninstall the PaperForge git pre-commit hook."""
    # STEP 1 — Find git root
    git_root = _find_git_root(project_root)
    if git_root is None:
        console.print(
            "[red]No git repository found. Initialize git first: git init[/red]"
        )
        sys.exit(1)

    hook_path = git_root / ".git" / "hooks" / "pre-commit"

    # STEP 2 — Handle --uninstall
    if uninstall:
        if hook_path.exists() and "paperforge" in hook_path.read_text(encoding="utf-8"):
            hook_path.unlink()
            console.print("[green]PaperForge git hook uninstalled.[/green]")
        else:
            console.print("[yellow]No PaperForge hook found to uninstall.[/yellow]")
        return

    # STEP 3 — Install pre-commit hook
    if hook_path.exists():
        existing_content = hook_path.read_text(encoding="utf-8")
        if "paperforge" not in existing_content:
            warn_text = Text()
            warn_text.append(
                "A pre-commit hook already exists and was not created by PaperForge.\n"
            )
            warn_text.append(f"Existing hook: {hook_path}\n")
            warn_text.append(
                "To install PaperForge alongside it, manually add:\n"
            )
            warn_text.append("  paperforge doctor\n")
            warn_text.append("to your existing hook file.")
            console.print(Panel(warn_text, border_style="yellow"))
            sys.exit(1)
        else:
            console.print("[yellow]PaperForge hook already installed.[/yellow]")
            return

    # Ensure hooks directory exists
    hook_path.parent.mkdir(parents=True, exist_ok=True)

    hook_path.write_text(HOOK_CONTENT, encoding="utf-8")
    hook_path.chmod(0o755)

    # STEP 4 — Print confirmation
    confirm_text = Text()
    confirm_text.append(f"Hook: {hook_path}\n\n")
    confirm_text.append(
        "PaperForge will now run `paperforge doctor` before every commit.\n"
    )
    confirm_text.append("Commits are blocked if any ERRORs exist.\n")
    confirm_text.append("Warnings do not block commits.\n")
    confirm_text.append("\nTo uninstall:\n")
    confirm_text.append("      paperforge install-hooks --uninstall\n")
    confirm_text.append("\nTo test the hook:\n")
    confirm_text.append("      git commit --allow-empty -m \"test\"")

    console.print(Panel(confirm_text, title="Git Hook Installed", border_style="green"))
