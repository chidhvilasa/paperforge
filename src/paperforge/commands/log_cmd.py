"""paperforge log command — show change history for a claim."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from paperforge.history import diff_snapshots, load_history

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def run(claim_id: str, project_root: Path, limit: int) -> None:
    if not (project_root / ".paperforge").exists():
        console.print("[red]Not a PaperForge project. Run `paperforge init` first.[/red]")
        sys.exit(1)

    claim_file = project_root / ".paperforge" / "claims" / f"{claim_id}.yaml"
    if not claim_file.exists():
        console.print(f"[red]Claim '{claim_id}' not found in .paperforge/claims/[/red]")
        sys.exit(1)

    snapshots = load_history(project_root / ".paperforge", claim_id)

    if not snapshots:
        console.print(
            Panel(
                f"No history found for {claim_id}.\n"
                "History is recorded when PaperForge writes a claim.\n"
                "Capture or edit the claim to start building history.",
                border_style="yellow",
            )
        )
        return

    snapshots = snapshots[:limit]

    current = yaml.safe_load(claim_file.read_text(encoding="utf-8"))

    console.print(f"[bold]History: {claim_id}[/bold]")
    console.print(f"  Current status: {current.get('status', 'unknown')}")
    console.print(f"  Showing {len(snapshots)} snapshot(s)")
    console.print("─" * 55)

    for i, snapshot in enumerate(snapshots):
        text = snapshot.snapshot.get("text") or "(empty)"
        content = Text(
            f"status:     {snapshot.snapshot.get('status', 'unknown')}\n"
            f"experiment: {snapshot.snapshot.get('experiment') or '(none)'}\n"
            f"sections:   {', '.join(snapshot.snapshot.get('sections', [])) or '(none)'}\n"
            f"text:       {text[:120]}"
        )
        title = Text(
            f"{snapshot.recorded_at.strftime('%Y-%m-%d %H:%M UTC')}  "
            f"[{snapshot.recorded_by}]"
        )
        console.print(Panel(content, title=title, border_style="blue"))

        if i < len(snapshots) - 1:
            changes = diff_snapshots(snapshots[i + 1].snapshot, snapshot.snapshot)
            if changes:
                changed_fields = ", ".join(sorted(changes.keys()))
                console.print(Text(f"Changed from previous: {changed_fields}", style="dim"))
