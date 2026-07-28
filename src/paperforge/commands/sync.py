"""paperforge sync command — bidirectional sync between paper_information/ and .paperforge/."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from paperforge.core.project import PaperForgeProject

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def _sync_to_md(project_root: Path, project: PaperForgeProject, force: bool) -> None:
    """Write .paperforge/claims/ → paper_information/content/*.md.

    Claims are source of truth. Groups by section, preserves subsection headers.
    """
    pf_dir = project_root / ".paperforge"
    info_dir = project_root / project.config.paper_information_dir
    content_dir = info_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    # Group claims by section
    section_claims: dict[str, list] = {}
    for claim in sorted(project.claims, key=lambda c: c.id):
        for sec in claim.sections:
            section_claims.setdefault(sec, []).append(claim)

    written: list[str] = []
    for section, claims in section_claims.items():
        md_path = content_dir / f"{section}.md"
        if md_path.exists() and not force:
            # Check if .md is newer than any claim
            md_mtime = md_path.stat().st_mtime
            claims_dir = pf_dir / "claims"
            any_newer = any(
                (claims_dir / f"{c.id}.yaml").stat().st_mtime > md_mtime
                for c in claims
                if (claims_dir / f"{c.id}.yaml").exists()
            )
            if not any_newer:
                console.print(
                    f"[dim]  {section}.md is up to date — skipping (use --force to overwrite)[/dim]"
                )
                continue

        lines: list[str] = [f"# {section.replace('_', ' ').title()}\n"]
        current_subsection = ""

        # Separate contribution claims
        non_contrib = [c for c in claims if not c.is_contribution]
        contrib = [c for c in claims if c.is_contribution]

        for claim in non_contrib:
            if claim.subsection and claim.subsection != current_subsection:
                lines.append(f"\n## {claim.subsection}\n")
                current_subsection = claim.subsection
            lines.append(f"\n{claim.text}\n")

        if contrib:
            lines.append("\n## Contributions\n")
            for claim in contrib:
                lines.append(f"\n- {claim.text}\n")

        md_path.write_text("".join(lines), encoding="utf-8")
        written.append(section)

    body_lines = [Text("Sections written to paper_information/content/:")]
    for sec in written:
        body_lines.append(Text(f"  {sec}.md ✓"))
    if not written:
        body_lines.append(Text("  (no sections needed updating)"))
    console.print(Panel(Text("\n").join(body_lines), title="Sync → MD", border_style="green"))


def _sync_to_claims(project_root: Path, force: bool) -> None:
    """Same as paperforge import with merge mode.

    Delegates to import_content.run() for round-trip use.
    """
    from paperforge.commands.import_content import run as import_run
    import_run(project_root=project_root, section=None, force=force)


def _sync_status(project_root: Path, project: PaperForgeProject) -> None:
    """Show sync status for each section."""
    info_dir = project_root / project.config.paper_information_dir
    content_dir = info_dir / "content"
    pf_dir = project_root / ".paperforge"
    claims_dir = pf_dir / "claims"

    # Find all sections from both .md files and claims
    sections_from_md: set[str] = set()
    if content_dir.exists():
        for md_file in content_dir.glob("*.md"):
            sections_from_md.add(md_file.stem)

    sections_from_claims: dict[str, list[str]] = {}
    for claim in project.claims:
        for sec in claim.sections:
            sections_from_claims.setdefault(sec, []).append(claim.id)

    all_sections = sorted(sections_from_md | set(sections_from_claims.keys()))

    table = Table(title="Sync Status", show_header=True, header_style="bold cyan")
    table.add_column("Section", style="cyan")
    table.add_column("MD Last Modified")
    table.add_column("Claims Last Modified")
    table.add_column("Claims Count")
    table.add_column("In Sync")

    for sec in all_sections:
        md_path = content_dir / f"{sec}.md" if content_dir.exists() else None
        claim_ids = sections_from_claims.get(sec, [])

        md_mtime_str = "—"
        if md_path and md_path.exists():
            md_mtime = datetime.fromtimestamp(md_path.stat().st_mtime, tz=UTC)
            md_mtime_str = md_mtime.strftime("%Y-%m-%d %H:%M")

        claim_mtime_str = "—"
        claims_newest = 0.0
        for cid in claim_ids:
            cp = claims_dir / f"{cid}.yaml"
            if cp.exists():
                mt = cp.stat().st_mtime
                claims_newest = max(claims_newest, mt)
        if claims_newest > 0:
            claim_mtime_str = datetime.fromtimestamp(claims_newest, tz=UTC).strftime(
                "%Y-%m-%d %H:%M"
            )

        # In sync = md file exists and is not newer than claims (or no md)
        in_sync = "✓"
        if md_path and md_path.exists() and claims_newest > 0:
            if md_path.stat().st_mtime > claims_newest:
                in_sync = "⚠ MD newer"
            elif claims_newest > md_path.stat().st_mtime:
                in_sync = "⚠ Claims newer"
        elif md_path and md_path.exists() and not claim_ids:
            in_sync = "⚠ No claims"
        elif claim_ids and (not md_path or not md_path.exists()):
            in_sync = "⚠ No MD file"

        table.add_row(
            sec,
            md_mtime_str,
            claim_mtime_str,
            str(len(claim_ids)),
            in_sync,
        )

    console.print(table)


def run(
    project_root: Path,
    direction: str = "status",
    force: bool = False,
) -> None:
    """Run the sync command in the given direction."""
    pf_dir = project_root / ".paperforge"
    if not pf_dir.exists():
        console.print(
            "[red]Not a PaperForge project. Run `paperforge init` first.[/red]"
        )
        sys.exit(1)

    project = PaperForgeProject.load(project_root)

    if direction == "to-md":
        _sync_to_md(project_root, project, force)
    elif direction == "to-claims":
        _sync_to_claims(project_root, force)
    elif direction == "status":
        _sync_status(project_root, project)
    else:
        console.print(
            f"[red]Unknown direction '{direction}'. Use: to-md, to-claims, or status.[/red]"
        )
        sys.exit(1)
