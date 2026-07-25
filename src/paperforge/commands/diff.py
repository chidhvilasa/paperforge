"""paperforge diff command — compare a claim against history or its experiment."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from paperforge.history import diff_snapshots, load_history
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment
from paperforge.utils.numbers import extract_numbers, numbers_match

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def _closest_metric(value: float, metrics: dict[str, float]) -> tuple[str, float] | None:
    if not metrics:
        return None
    name, mv = min(metrics.items(), key=lambda kv: abs(kv[1] - value))
    return name, mv


def _diff_against_experiment(
    claim_id: str, current_claim: Claim, project_root: Path
) -> None:
    exp_id = current_claim.experiment
    if not exp_id:
        console.print(f"[red]{claim_id} has no linked experiment.[/red]")
        sys.exit(1)

    exp_file = project_root / ".paperforge" / "experiments" / f"{exp_id}.yaml"
    if not exp_file.exists():
        console.print(f"[red]Experiment '{exp_id}' not found.[/red]")
        sys.exit(1)

    exp_data = yaml.safe_load(exp_file.read_text(encoding="utf-8"))
    experiment = Experiment.from_yaml(exp_data)

    claim_numbers = [
        n for n in extract_numbers(current_claim.text) if n.is_percentage
    ]

    if not claim_numbers:
        console.print(
            f"[yellow]{claim_id} contains no percentage values to compare.[/yellow]"
        )
        return

    table = Table(title=f"Claim vs Experiment: {claim_id} vs {exp_id}")
    table.add_column("Claim Text Value")
    table.add_column("Closest Metric")
    table.add_column("Metric Value")
    table.add_column("Status")

    for claim_num in claim_numbers:
        closest = _closest_metric(claim_num.value, experiment.metrics)
        if closest is None:
            metric_name, metric_value, consistent = "no match", "--", False
        else:
            metric_name, mv = closest
            metric_value = str(mv)
            consistent = numbers_match(claim_num.value, mv)

        status = "✓ consistent" if consistent else "✗ mismatch"
        row_style = "green" if consistent else "red"
        table.add_row(claim_num.raw, metric_name, metric_value, status, style=row_style)

    console.print(table)


def _diff_against_previous(
    claim_id: str, current: dict[str, Any], project_root: Path
) -> None:
    snapshots = load_history(project_root / ".paperforge", claim_id)

    if not snapshots:
        console.print(
            f"[yellow]No history for {claim_id}. Cannot diff against previous.[/yellow]"
        )
        return

    most_recent = snapshots[0]
    changes = diff_snapshots(most_recent.snapshot, current)

    if not changes:
        console.print(
            Panel(
                Text(
                    f"{claim_id} is unchanged since last snapshot.\n"
                    f"Last recorded: {most_recent.recorded_at.strftime('%Y-%m-%d %H:%M UTC')}"
                ),
                border_style="green",
            )
        )
        return

    console.print(Text(f"Diff: {claim_id}", style="bold"))
    console.print(
        Text(
            f"vs snapshot from "
            f"{most_recent.recorded_at.strftime('%Y-%m-%d %H:%M UTC')} "
            f"[{most_recent.recorded_by}]"
        )
    )
    console.print()

    for field in sorted(changes.keys()):
        old_value, new_value = changes[field]
        console.print(Text(f"- {field}: {old_value}", style="red"))
        console.print(Text(f"+ {field}: {new_value}", style="green"))

    console.print()
    console.print(f"{len(changes)} field(s) changed")


def run(claim_id: str, project_root: Path, against: str) -> None:
    if not (project_root / ".paperforge").exists():
        console.print("[red]Not a PaperForge project. Run `paperforge init` first.[/red]")
        sys.exit(1)

    claim_file = project_root / ".paperforge" / "claims" / f"{claim_id}.yaml"
    if not claim_file.exists():
        console.print(f"[red]Claim '{claim_id}' not found.[/red]")
        sys.exit(1)

    current = yaml.safe_load(claim_file.read_text(encoding="utf-8"))
    current_claim = Claim.from_yaml(current)

    if against == "experiment":
        _diff_against_experiment(claim_id, current_claim, project_root)
    elif against in ("previous", "HEAD~1"):
        _diff_against_previous(claim_id, current, project_root)
    else:
        console.print(
            f"[red]Unknown diff target '{against}'. "
            "Use: previous, HEAD~1, experiment[/red]"
        )
        sys.exit(1)
