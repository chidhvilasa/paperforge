"""paperforge find command — full-text search across the research graph."""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from paperforge.core.project import PaperForgeProject

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def _highlight(text: str, query: str) -> Text:
    """Wrap occurrences of query (case-insensitive) with bold yellow markup."""
    result = Text()
    lower_text = text.lower()
    lower_query = query.lower()
    pos = 0
    while True:
        idx = lower_text.find(lower_query, pos)
        if idx == -1:
            result.append(text[pos:])
            break
        result.append(text[pos:idx])
        result.append(text[idx: idx + len(query)], style="bold yellow")
        pos = idx + len(query)
    return result


def run(query: str, project_root: Path, field: str | None = "all") -> None:
    """Case-insensitive full-text search across the research graph."""
    # STEP 1 — Validate
    if not (project_root / ".paperforge").exists():
        console.print(
            "[red]Not a PaperForge project. Run `paperforge init` first.[/red]"
        )
        sys.exit(1)

    if not query.strip():
        console.print("[red]Search query cannot be empty.[/red]")
        sys.exit(1)

    search_field = field or "all"
    project = PaperForgeProject.load(project_root)
    query_lower = query.strip().lower()

    claim_results = []
    experiment_results = []

    # STEP 2 — Search claims
    if search_field in ("claims", "all"):
        for claim in project.claims:
            haystack = " ".join([
                claim.text,
                claim.experiment,
                claim.id,
                " ".join(claim.sections),
                " ".join(claim.figures),
                " ".join(claim.tables),
                " ".join(claim.citations),
            ]).lower()
            if query_lower in haystack:
                claim_results.append(claim)

    # STEP 3 — Search experiments
    if search_field in ("experiments", "all"):
        for exp in project.experiments:
            metrics_str = " ".join(
                f"{k}:{v}" for k, v in exp.metrics.items()
            )
            haystack = " ".join([
                exp.id,
                exp.description or "",
                exp.dataset or "",
                exp.hardware or "",
                metrics_str,
            ]).lower()
            if query_lower in haystack:
                experiment_results.append(exp)

    # STEP 4 — Print results
    if not claim_results and not experiment_results:
        console.print(
            Panel(
                Text.assemble(
                    f"No results for '{query}'\n",
                    f"Searched: {search_field}",
                ),
                border_style="yellow",
            )
        )
        return

    console.print(Text(f"Search results for '{query}'", style="bold"))
    console.print()

    if claim_results:
        console.print(
            Text(f"Claims ({len(claim_results)} found)", style="bold")
        )
        for claim in claim_results:
            truncated = claim.text[:100] + ("..." if len(claim.text) > 100 else "")
            console.print(
                Text.assemble(
                    Text(f"  {claim.id}", style="cyan bold"),
                    Text(f"  ({claim.status})"),
                )
            )
            # Highlighted text
            highlighted = _highlight(truncated, query.strip())
            prefixed = Text("  ")
            prefixed.append_text(highlighted)
            console.print(prefixed)
            exp_label = claim.experiment or "none"
            sections_label = ", ".join(claim.sections) if claim.sections else "none"
            console.print(
                f"  Experiment: {exp_label} | Sections: {sections_label}"
            )
            console.print()

    if experiment_results:
        console.print(
            Text(f"Experiments ({len(experiment_results)} found)", style="bold")
        )
        for exp in experiment_results:
            desc = (exp.description or "(no description)")[:80]
            metric_names = ", ".join(exp.metrics.keys()) if exp.metrics else "none"
            console.print(Text(f"  {exp.id}", style="cyan bold"))
            console.print(f"  {desc}")
            console.print(f"  Metrics: {metric_names}")
            console.print(f"  Dataset: {exp.dataset or 'not specified'}")
            console.print()

    console.print(
        Text(
            f"Found {len(claim_results)} claim(s) and "
            f"{len(experiment_results)} experiment(s)",
            style="dim",
        )
    )
