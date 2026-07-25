"""paperforge capture command."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from paperforge.history import record_snapshot
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def _extract_metrics(data: dict) -> dict[str, float]:
    raw = data["metrics"] if isinstance(data.get("metrics"), dict) else data
    return {k: v for k, v in raw.items() if type(v) in (int, float)}


def _next_claim_id(claims_dir: Path) -> str:
    max_n = 0
    for claim_file in claims_dir.glob("claim_*.yaml"):
        suffix = claim_file.stem.removeprefix("claim_")
        if suffix.isdigit():
            max_n = max(max_n, int(suffix))
    return f"claim_{max_n + 1:02d}"


def run(results: Path, experiment_id: str, project_root: Path) -> None:
    if not (project_root / ".paperforge").exists():
        console.print("[red]Not a PaperForge project. Run `paperforge init` first.[/red]")
        sys.exit(1)

    if not results.exists():
        console.print(f"[red]Results file not found: {results}[/red]")
        sys.exit(1)

    if " " in experiment_id or "/" in experiment_id:
        console.print("[red]Experiment ID must not contain spaces or slashes.[/red]")
        sys.exit(1)

    try:
        data = json.loads(results.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        console.print(f"[red]Invalid JSON: {results}[/red]")
        sys.exit(1)

    new_metrics = _extract_metrics(data)

    experiments_dir = project_root / ".paperforge" / "experiments"
    experiment_path = experiments_dir / f"{experiment_id}.yaml"

    is_new = not experiment_path.exists()
    if is_new:
        experiment = Experiment(id=experiment_id, metrics=new_metrics)
    else:
        existing = Experiment.from_yaml(
            yaml.safe_load(experiment_path.read_text(encoding="utf-8"))
        )
        existing.metrics.update(new_metrics)
        experiment = existing

    experiment_path.write_text(
        yaml.dump(experiment.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    claims_dir = project_root / ".paperforge" / "claims"
    claim_id = _next_claim_id(claims_dir)
    claim_path = claims_dir / f"{claim_id}.yaml"

    if claim_path.exists():
        current_data = yaml.safe_load(claim_path.read_text(encoding="utf-8"))
        record_snapshot(
            paperforge_dir=project_root / ".paperforge",
            claim_id=claim_id,
            claim_data=current_data,
            recorded_by="paperforge capture",
        )

    claim = Claim(id=claim_id, text="", experiment=experiment_id)
    claim_path.write_text(
        yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    metrics_table = Table(show_header=False, box=None, padding=(0, 2, 0, 2))
    metrics_table.add_column("name")
    metrics_table.add_column("value", justify="right")
    for name, value in experiment.metrics.items():
        metrics_table.add_row(name, str(value))

    status_verb = "Created" if is_new else "Updated"
    body = Group(
        Text(f"Experiment: {experiment_id}"),
        Text(f"{status_verb}: .paperforge/experiments/{experiment_id}.yaml"),
        Text(""),
        Text("Metrics:"),
        metrics_table,
        Text(""),
        Text(f"Draft claim created: .paperforge/claims/{claim_id}.yaml"),
        Text(""),
        Text(
            "Next steps:\n"
            "  1. Open .paperforge/claims/"
            f"{claim_id}.yaml\n"
            "  2. Fill in the `text` field — the exact sentence "
            "as it will appear in your paper\n"
            "  3. Add figures, tables, citations, and sections as you write\n"
            "  4. Run `paperforge doctor` to check consistency"
        ),
    )

    console.print(Panel(body, title="Captured", border_style="green"))
