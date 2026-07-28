"""paperforge clean command — remove stale build artifacts and aux files."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from rich.console import Console

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()

AUX_EXTENSIONS = {
    ".aux",
    ".log",
    ".fls",
    ".fdb_latexmk",
    ".out",
    ".bbl",
    ".blg",
    ".synctex.gz",
    ".toc",
    ".lof",
    ".lot",
}


def run(project_root: Path) -> None:
    """Remove stale paper_generated/ at project root and LaTeX aux files."""
    removed: list[str] = []

    # Remove stale root-level paper_generated/ when output is configured elsewhere
    try:
        from paperforge.core.project import PaperForgeProject

        project = PaperForgeProject.load(project_root)
        configured = project_root / project.config.build_output_dir
        stale = project_root / "paper_generated"
        try:
            if stale.exists() and not configured.is_relative_to(stale):
                shutil.rmtree(stale)
                removed.append("paper_generated/ (stale root copy)")
        except (AttributeError, TypeError, OSError):
            pass
    except (FileNotFoundError, OSError, ValueError):
        pass

    # Remove aux files from common paper_generated subdirs
    candidate_dirs = [
        project_root / "paper" / "paper_generated",
        project_root / "paper_generated",
    ]
    for pgen in candidate_dirs:
        if pgen.exists():
            for f in pgen.rglob("*"):
                if f.is_file() and f.suffix in AUX_EXTENSIONS:
                    try:
                        f.unlink()
                        removed.append(f.name)
                    except OSError:
                        pass

    if removed:
        console.print(f"[green]Cleaned {len(removed)} item(s)[/green]")
        for item in removed:
            console.print(f"  [dim]removed: {item}[/dim]")
    else:
        console.print("[dim]Nothing to clean.[/dim]")
