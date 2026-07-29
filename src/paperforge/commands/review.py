"""paperforge review command."""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from paperforge.commands.doctor import collect_issues
from paperforge.core.project import PaperForgeProject
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()

MAX_CONTEXT_TOKENS = 4000
MAX_CLAIMS_BEFORE_TRUNCATION = 20

PROMPT_TEMPLATE = """You are reviewing a research paper draft.
The paper is described below as structured data extracted
from the author's research dependency graph.

{context}

Review this paper draft and provide feedback in exactly
these six categories. Be specific. Reference claim IDs
where relevant.

1. NOVELTY
   Is the contribution clearly stated? Which claims establish
   novelty? Are there gaps in the novelty argument?

2. EVIDENCE COVERAGE
   Are all major claims backed by experiments? List any
   claims that appear unsupported or weakly supported.

3. CONSISTENCY
   Are there contradictions between claims, sections,
   or experiments? Note any terminology inconsistencies.

4. WRITING CLARITY
   Which sections or claims are unclear or ambiguous?
   Identify passive voice overuse or vague language.

5. REVIEWER SIMULATION
   As a likely IEEE reviewer, what are the top 3 reasons
   this paper might be rejected? Be harsh and specific.

6. SUGGESTED IMPROVEMENTS
   List the 3 highest-impact changes the author should make
   before submission. Prioritize by impact.

Format your response with these exact headings.
Be direct. Do not soften criticism.
Do not invent results or claims not present in the data above.
"""


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _format_claim(claim: Claim) -> str:
    return (
        f"[{claim.id}] ({claim.status})\n"
        f"Text: {claim.text}\n"
        f"Evidence: {claim.experiment}\n"
        f"Sections: {', '.join(claim.sections)}\n"
        f"Figures: {', '.join(claim.figures) or 'none'}\n"
        f"Tables: {', '.join(claim.tables) or 'none'}\n"
        f"Citations: {', '.join(claim.citations) or 'none'}"
    )


def _format_experiment(experiment: Experiment) -> str:
    metrics = ", ".join(f"{k}: {v}" for k, v in experiment.metrics.items()) or "none"
    return (
        f"[{experiment.id}]\n"
        f"Description: {experiment.description or 'none'}\n"
        f"Dataset: {experiment.dataset or 'not specified'}\n"
        f"Hardware: {experiment.hardware or 'not specified'}\n"
        f"Key Metrics: {metrics}"
    )


def _build_context(project: PaperForgeProject) -> str:
    claims = project.claims

    def render(claims_to_render: list[Claim]) -> str:
        warnings = [i for i in collect_issues(project) if i.severity == "WARNING"]

        lines = [
            f"PAPER TITLE: {project.config.title}",
            f"AUTHORS: {', '.join(str(a) for a in project.config.authors)}",
            f"VENUE: {project.config.venue or 'Not specified'}",
            f"SECTIONS: {', '.join(project.config.sections)}",
            "",
            f"CLAIMS ({len(claims_to_render)} total):",
        ]
        for claim in claims_to_render:
            lines.append(_format_claim(claim))
            lines.append("")

        lines.append(f"EXPERIMENTS ({len(project.experiments)} total):")
        for experiment in project.experiments:
            lines.append(_format_experiment(experiment))
            lines.append("")

        lines.append(f"DOCTOR WARNINGS ({len(warnings)} total):")
        for warning in warnings:
            lines.append(f"[{warning.code}] {warning.message}")

        return "\n".join(lines)

    context = render(claims)
    if _estimate_tokens(context) > MAX_CONTEXT_TOKENS and len(claims) > (
        MAX_CLAIMS_BEFORE_TRUNCATION
    ):
        truncated_count = len(claims) - MAX_CLAIMS_BEFORE_TRUNCATION
        context = render(claims[:MAX_CLAIMS_BEFORE_TRUNCATION])
        context += f"\n\n... {truncated_count} additional claims truncated."

    return context


def run(project_root: Path, model: str | None) -> None:
    if not (project_root / ".paperforge").exists():
        console.print("[red]Not a PaperForge project. Run `paperforge init` first.[/red]")
        sys.exit(1)

    project = PaperForgeProject.load(project_root)
    issues = collect_issues(project)
    errors = [issue for issue in issues if issue.severity == "ERROR"]

    if errors:
        body = Group(
            Text("Review blocked. Fix all ERRORs before running review."),
            *(Text(f"  [{issue.code}] {issue.message}") for issue in errors),
            Text("Run `paperforge doctor` for full details."),
        )
        console.print(Panel(body, border_style="red"))
        sys.exit(1)

    if shutil.which("llm") is None:
        console.print("[red]llm is not available on PATH.[/red]")
        console.print("[red]Install it with: uv add llm[/red]")
        console.print("[red]Then configure a model: llm keys set openai[/red]")
        sys.exit(1)

    context = _build_context(project)
    prompt = PROMPT_TEMPLATE.format(context=context)

    cmd = ["llm", "prompt"]
    if model:
        cmd += ["-m", model]
    cmd += [prompt]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        console.print("[red]llm call failed.[/red]")
        console.print(f"[red]{result.stderr}[/red]")
        console.print("[red]Check your llm configuration: llm models list[/red]")
        sys.exit(1)

    console.print(
        Panel(result.stdout, title="AI Review", border_style="yellow")
    )

    review_dir = project_root / ".paperforge" / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / "latest_review.md"
    review_path.write_text(
        "# PaperForge AI Review\n"
        f"# Generated: {datetime.now().astimezone().isoformat()}\n"
        f"# Model: {model or 'llm default'}\n"
        "# WARNING: AI output is advisory only.\n"
        "#          It is never a source of truth.\n"
        "#          Verify all suggestions against your research.\n"
        "\n"
        f"{result.stdout}",
        encoding="utf-8",
    )

    gitignore_path = project_root / ".paperforge" / ".gitignore"
    gitignore_content = gitignore_path.read_text(encoding="utf-8")
    if "review/" not in gitignore_content:
        gitignore_path.write_text(
            gitignore_content
            + "\n# AI review outputs — advisory only, not part of research record\n"
            "review/\n",
            encoding="utf-8",
        )

    console.print("Review saved to .paperforge/review/latest_review.md")
    console.print("This output is advisory only. Verify all suggestions.")
