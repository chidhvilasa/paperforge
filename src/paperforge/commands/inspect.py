"""paperforge inspect command — read-only project reconnaissance.

Detects what already exists in a directory (manuscripts, bibliography,
figures, data, notebooks, package managers, Git state, likely secrets,
absolute paths, existing PaperForge state) before any intake, import, or
generation decision is made. Never modifies or executes anything found.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()

# Directories never descended into during inspection -- build artifacts,
# dependency caches, and version-control internals are not project content.
_EXCLUDED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "backups",
    "audit_output",
    "dist",
    "build",
    "paper_generated",
}

_MANUSCRIPT_EXTS = {".tex", ".docx"}
_MARKDOWN_EXTS = {".md", ".markdown"}
_BIB_EXTS = {".bib"}
_FIGURE_EXTS = {".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg", ".tiff", ".tif"}
_TABLE_EXTS = {".csv", ".tsv"}
_NOTEBOOK_EXTS = {".ipynb"}
_DATA_EXTS = {".csv", ".tsv", ".json", ".parquet", ".xlsx", ".h5", ".npz", ".npy"}
_VENUE_TEMPLATE_EXTS = {".cls", ".sty", ".bst"}
_PACKAGE_MANAGER_FILES = {
    "pyproject.toml",
    "requirements.txt",
    "Pipfile",
    "environment.yml",
    "package.json",
    "Cargo.toml",
    "go.mod",
}

# Deliberately conservative: high-confidence secret shapes only, to avoid
# false alarms on ordinary source/config text. This is a heuristic scan
# for the researcher's/agent's attention, not a security scanner.
_SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key block"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key ID"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "API-key-shaped token (sk-...)"),
    (re.compile(r"\bghp_[A-Za-z0-9]{36}\b"), "GitHub personal access token"),
    (
        re.compile(r"(?i)\bpassword\s*[:=]\s*['\"][^'\"\s]{4,}['\"]"),
        "hardcoded password literal",
    ),
]

_ABS_PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:\\\\?Users\\\\?[A-Za-z0-9_.\-]+"),
    re.compile(r"/home/[a-zA-Z0-9_.\-]+"),
    re.compile(r"/Users/[a-zA-Z0-9_.\-]+"),
]

_TEXT_SCAN_EXTS = {
    ".tex",
    ".md",
    ".markdown",
    ".yaml",
    ".yml",
    ".py",
    ".sh",
    ".ps1",
    ".txt",
    ".cfg",
    ".ini",
}
_MAX_TEXT_SCAN_BYTES = 2_000_000  # skip scanning unusually large text files


@dataclass
class InspectionReport:
    root: str
    is_git_repo: bool
    git_branch: str = ""
    git_dirty: bool | None = None
    has_paperforge_project: bool = False
    paperforge_manifest_path: str = ""
    manuscripts: list[str] = field(default_factory=list)
    markdown_files: list[str] = field(default_factory=list)
    bibliography_files: list[str] = field(default_factory=list)
    figures: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    notebooks: list[str] = field(default_factory=list)
    data_files: list[str] = field(default_factory=list)
    venue_template_files: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    candidate_output_dirs: list[str] = field(default_factory=list)
    likely_secrets: list[dict[str, str]] = field(default_factory=list)
    absolute_paths: list[dict[str, str]] = field(default_factory=list)
    files_scanned: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "is_git_repo": self.is_git_repo,
            "git_branch": self.git_branch,
            "git_dirty": self.git_dirty,
            "has_paperforge_project": self.has_paperforge_project,
            "paperforge_manifest_path": self.paperforge_manifest_path,
            "manuscripts": self.manuscripts,
            "markdown_files": self.markdown_files,
            "bibliography_files": self.bibliography_files,
            "figures": self.figures,
            "tables": self.tables,
            "notebooks": self.notebooks,
            "data_files": self.data_files,
            "venue_template_files": self.venue_template_files,
            "package_managers": self.package_managers,
            "candidate_output_dirs": self.candidate_output_dirs,
            "likely_secrets": self.likely_secrets,
            "absolute_paths": self.absolute_paths,
            "files_scanned": self.files_scanned,
        }


def _git_state(root: Path) -> tuple[bool, str, bool | None]:
    if not (root / ".git").exists():
        return False, "", None
    try:
        branch = subprocess.run(
            ["git", "-C", str(root), "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        ).stdout
        return True, branch, bool(status.strip())
    except (OSError, subprocess.SubprocessError):
        return True, "", None


def run_inspection(project_root: Path) -> InspectionReport:
    """Walk `project_root` read-only and report what already exists.

    Never executes, imports, or modifies anything it finds.
    """
    is_git_repo, git_branch, git_dirty = _git_state(project_root)
    report = InspectionReport(
        root=str(project_root),
        is_git_repo=is_git_repo,
        git_branch=git_branch,
        git_dirty=git_dirty,
    )

    pf_dir = project_root / ".paperforge"
    if pf_dir.exists():
        report.has_paperforge_project = True
        manifest = pf_dir / "paper.yaml"
        if manifest.exists():
            report.paperforge_manifest_path = str(manifest)

    for f in project_root.rglob("*"):
        if not f.is_file():
            continue
        if any(
            part in _EXCLUDED_DIR_NAMES
            for part in f.relative_to(project_root).parts[:-1]
        ):
            continue
        report.files_scanned += 1
        ext = f.suffix.lower()
        rel = f.relative_to(project_root).as_posix()

        if ext in _MANUSCRIPT_EXTS:
            report.manuscripts.append(rel)
        if ext in _MARKDOWN_EXTS:
            report.markdown_files.append(rel)
        if ext in _BIB_EXTS:
            report.bibliography_files.append(rel)
        if ext in _FIGURE_EXTS:
            report.figures.append(rel)
        if ext in _TABLE_EXTS:
            report.tables.append(rel)
        if ext in _NOTEBOOK_EXTS:
            report.notebooks.append(rel)
        if ext in _DATA_EXTS and ext not in _TABLE_EXTS:
            report.data_files.append(rel)
        if ext in _VENUE_TEMPLATE_EXTS:
            report.venue_template_files.append(rel)
        if f.name in _PACKAGE_MANAGER_FILES:
            report.package_managers.append(rel)

        if ext in _TEXT_SCAN_EXTS:
            try:
                if f.stat().st_size > _MAX_TEXT_SCAN_BYTES:
                    continue
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pat, label in _SECRET_PATTERNS:
                if pat.search(text):
                    report.likely_secrets.append({"file": rel, "kind": label})
            for pat in _ABS_PATH_PATTERNS:
                m = pat.search(text)
                if m:
                    report.absolute_paths.append({"file": rel, "match": m.group(0)})
                    break

    for candidate_name in ("paper_generated", "output", "build_output"):
        d = project_root / candidate_name
        if d.is_dir():
            report.candidate_output_dirs.append(d.relative_to(project_root).as_posix())

    for lst in (
        report.manuscripts,
        report.markdown_files,
        report.bibliography_files,
        report.figures,
        report.tables,
        report.notebooks,
        report.data_files,
        report.venue_template_files,
        report.package_managers,
    ):
        lst.sort()

    return report


def _print_report(report: InspectionReport) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    table.add_column("key", style="bold")
    table.add_column("value")
    table.add_row("Git repository:", "yes" if report.is_git_repo else "no")
    if report.is_git_repo:
        table.add_row("  Branch:", report.git_branch or "(detached)")
        table.add_row(
            "  Working tree:",
            "dirty"
            if report.git_dirty
            else ("clean" if report.git_dirty is False else "unknown"),
        )
    table.add_row(
        "Existing PaperForge project:",
        "yes" if report.has_paperforge_project else "no",
    )
    table.add_row("Manuscript files (.tex/.docx):", str(len(report.manuscripts)))
    table.add_row("Markdown files:", str(len(report.markdown_files)))
    table.add_row("Bibliography files (.bib):", str(len(report.bibliography_files)))
    table.add_row("Figures:", str(len(report.figures)))
    table.add_row("Tables (.csv/.tsv):", str(len(report.tables)))
    table.add_row("Notebooks (.ipynb):", str(len(report.notebooks)))
    table.add_row("Other data files:", str(len(report.data_files)))
    table.add_row(
        "Venue template files (.cls/.sty/.bst):", str(len(report.venue_template_files))
    )
    table.add_row(
        "Package managers detected:", ", ".join(report.package_managers) or "(none)"
    )
    table.add_row(
        "Candidate output directories:",
        ", ".join(report.candidate_output_dirs) or "(none)",
    )
    table.add_row("Files scanned:", str(report.files_scanned))

    body: list[Any] = [table]

    if report.likely_secrets:
        body.append(Text(""))
        body.append(
            Text(
                "⚠ Possible secrets detected — review before sharing this directory:",
                style="bold red",
            )
        )
        for s in report.likely_secrets:
            body.append(Text(f"  • {s['file']}: {s['kind']}", style="red"))

    if report.absolute_paths:
        body.append(Text(""))
        body.append(
            Text(
                "⚠ Absolute local paths found — not portable if committed/packaged:",
                style="bold yellow",
            )
        )
        for p in report.absolute_paths[:10]:
            body.append(Text(f"  • {p['file']}: {p['match']}", style="yellow"))

    from rich.console import Group

    console.print(
        Panel(
            Group(*body),
            title="PaperForge Inspect",
            border_style="green" if not report.likely_secrets else "red",
        )
    )


def run(project_root: Path, json_output: bool = False) -> None:
    report = run_inspection(project_root)
    if json_output:
        print(json.dumps(report.to_dict(), indent=2))
        return
    _print_report(report)
