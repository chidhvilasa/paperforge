"""paperforge improve command — AI-assisted claim improvement."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from paperforge.commands.doctor import Issue, collect_issues
from paperforge.core.project import PaperForgeProject
from paperforge.history import record_snapshot
from paperforge.models.claim import Claim

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def _build_improvement_prompt(
    claim: Claim,
    project: PaperForgeProject,
    issues: list[Issue],
) -> str:
    exp = next(
        (e for e in project.experiments if e.id == claim.experiment),
        None,
    )
    metrics_str = ""
    if exp and exp.metrics:
        metrics_str = "\n".join(
            f"  {k}: {v}" for k, v in exp.metrics.items()
        )

    claim_issues = [
        i for i in issues
        if claim.id in i.message
    ]
    issues_str = "\n".join(
        f"  [{i.severity}] {i.code}: {i.message}"
        for i in claim_issues
    ) or "  None"

    return f"""You are helping improve a scientific claim for an IEEE journal paper.

CLAIM ID: {claim.id}
CURRENT TEXT: {claim.text or "(empty)"}
STATUS: {claim.status}
SECTIONS: {", ".join(claim.sections) or "none"}
CITATIONS: {", ".join(claim.citations) or "none"}

LINKED EXPERIMENT: {claim.experiment or "none"}
EXPERIMENT METRICS:
{metrics_str or "  (no metrics)"}

DOCTOR ISSUES FOR THIS CLAIM:
{issues_str}

TASK: Suggest improvements to this claim text. Focus on:
1. Scientific precision — does the text accurately reflect the metrics?
2. IEEE journal style — active voice, clear contribution statement
3. Completeness — are all key metrics mentioned?
4. Citation needs — does this claim need a citation?

RULES:
- Do NOT invent numbers not present in the experiment metrics above
- Do NOT change the fundamental finding
- Keep the claim as a single sentence where possible
- If the text is already good, say so explicitly

OUTPUT FORMAT (use exactly this structure):

ASSESSMENT: [one sentence: is this claim strong or weak?]

ISSUES:
- [list specific problems, or "None found"]

SUGGESTED TEXT:
[your improved version of the claim text, or "No change needed"]

REASONING: [one sentence explaining the key improvement made]
"""


def _extract_suggested_text(llm_output: str) -> str | None:
    if "SUGGESTED TEXT:" not in llm_output or "REASONING:" not in llm_output:
        return None
    try:
        after_suggested = llm_output.split("SUGGESTED TEXT:", 1)[1]
        suggested_block = after_suggested.split("REASONING:", 1)[0].strip()
        if not suggested_block or suggested_block.lower() == "no change needed":
            return None
        return suggested_block
    except (IndexError, ValueError):
        return None


def run(
    project_root: Path,
    claim_id: str | None,
    model: str | None,
    all_claims: bool,
) -> None:
    pf_dir = project_root / ".paperforge"
    if not pf_dir.exists():
        console.print("[red]Not a PaperForge project. Run `paperforge init` first.[/red]")
        sys.exit(1)

    if not claim_id and not all_claims:
        console.print("[red]Specify a claim ID or use --all.[/red]")
        console.print("  paperforge improve claim_01")
        console.print("  paperforge improve --all")
        sys.exit(1)

    if shutil.which("llm") is None:
        console.print("[red]llm is not available on PATH.[/red]")
        console.print("[red]Install it with: uv add llm[/red]")
        console.print("[red]Then configure a model: llm keys set openai[/red]")
        sys.exit(1)

    project = PaperForgeProject.load(project_root)
    issues = collect_issues(project)

    if claim_id:
        target_claim = next((c for c in project.claims if c.id == claim_id), None)
        if not target_claim:
            console.print(f"[red]Claim '{claim_id}' not found.[/red]")
            sys.exit(1)
        claims_to_improve = [target_claim]
    else:
        claims_to_improve = [c for c in project.claims if c.status != "verified"]
        if not claims_to_improve:
            console.print("[yellow]No unverified claims found to improve.[/yellow]")
            return

    reviewed_count = 0
    updated_count = 0
    skipped_count = 0

    for claim in claims_to_improve:
        reviewed_count += 1
        console.print(
            Panel(claim.text or "(empty)", title=f"Improving {claim.id}", border_style="cyan")
        )

        prompt = _build_improvement_prompt(claim, project, issues)
        cmd = ["llm", "prompt"]
        if model:
            cmd += ["-m", model]
        cmd += [prompt]

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            console.print(f"[red]llm call failed for {claim.id}: {result.stderr}[/red]")
            skipped_count += 1
            continue

        console.print(
            Panel(result.stdout, title=f"Suggestions for {claim.id}", border_style="yellow")
        )

        suggested_text = _extract_suggested_text(result.stdout)
        if suggested_text is None:
            console.print(
                "[yellow]Could not extract valid suggested text or no change recommended. Skipping.[/yellow]"
            )
            skipped_count += 1
            continue

        console.print("\nApply suggested text? [y/n/s(kip all)]")
        choice = typer.prompt("Choice", default="n").strip().lower()

        if choice == "y":
            claim_file = pf_dir / "claims" / f"{claim.id}.yaml"
            record_snapshot(pf_dir, claim.id, claim.to_yaml(), "improve")
            claim.text = suggested_text
            claim_file.write_text(
                yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
                encoding="utf-8",
            )
            updated_count += 1
            console.print(f"[green]✓ {claim.id} updated.[/green]")
        elif choice == "s":
            skipped_count += 1
            console.print("[dim]Skipping all remaining claims.[/dim]")
            break
        else:
            skipped_count += 1
            console.print("[dim]Skipped.[/dim]")

    summary_text = (
        f"Claims reviewed: {reviewed_count}\n"
        f"Claims updated:  {updated_count}\n"
        f"Claims skipped:  {skipped_count}\n\n"
        "Run `paperforge doctor` to check consistency after updates."
    )
    console.print(Panel(summary_text, title="Improve Complete", border_style="green"))
