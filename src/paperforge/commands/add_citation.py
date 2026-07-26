"""paperforge add-citation command."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from paperforge.core.project import PaperForgeProject
from paperforge.models.citation import Citation, CitationType

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()

VALID_TYPES = (
    "article",
    "inproceedings",
    "book",
    "techreport",
    "misc",
    "phdthesis",
    "mastersthesis",
    "online",
)


def run(project_root: Path, key: str | None = None) -> None:
    if not (project_root / ".paperforge").exists():
        console.print("[red]Not a PaperForge project. Run `paperforge init` first.[/red]")
        sys.exit(1)

    project = PaperForgeProject.load(project_root)

    cit_keys = [c.key for c in project.citations]
    existing_cits = ", ".join(sorted(cit_keys)) if cit_keys else "none"

    all_claimed_keys = {k for claim in project.claims for k in claim.citations}
    undefined_keys = sorted(all_claimed_keys - set(cit_keys))
    undefined_str = ", ".join(undefined_keys) if undefined_keys else "none"

    console.print(
        Panel(
            f"Existing citations: {existing_cits}\n"
            f"Claim citation keys (undefined): {undefined_str}\n\n"
            f"Fill in citation details below.",
            title="Add Citation",
            border_style="cyan",
        )
    )

    if not key:
        console.print("[bold]BibTeX key[/bold] — e.g. smith2024, jones2023b")
        key = typer.prompt("Key").strip()
    else:
        key = key.strip()

    citations_dir = project_root / ".paperforge" / "citations"
    cit_path = citations_dir / f"{key}.yaml"
    if cit_path.exists():
        console.print(f"[yellow]Citation '{key}' already exists. Overwriting.[/yellow]")

    console.print("[bold]Type[/bold] — article, inproceedings, book, techreport, misc")
    type_val = typer.prompt("Type", default="article").strip().lower()
    type_str: CitationType = cast(CitationType, type_val if type_val in VALID_TYPES else "article")

    console.print("[bold]Authors[/bold] — comma-separated, Last, First format")
    console.print("  Separate multiple authors with semicolons: Smith, A.; Jones, B.")
    raw_authors = typer.prompt("Authors", default="")
    authors = [a.strip() for a in raw_authors.split(";") if a.strip()]

    console.print("[bold]Title[/bold]")
    title = typer.prompt("Title", default="")

    console.print("[bold]Year[/bold]")
    raw_year = typer.prompt("Year", default="")
    year = int(raw_year) if raw_year.strip().isdigit() else None

    console.print("[bold]Venue[/bold] — journal name, conference name, etc.")
    venue = typer.prompt("Venue", default="")

    console.print("[bold]Volume[/bold] — journal volume number (leave empty if N/A)")
    volume = typer.prompt("Volume", default="")

    console.print("[bold]Issue/Number[/bold] — journal issue (leave empty if N/A)")
    number = typer.prompt("Issue", default="")

    console.print("[bold]Pages[/bold] — e.g. 123--135 or 1-10")
    pages = typer.prompt("Pages", default="")

    console.print("[bold]DOI[/bold] — without https://doi.org/ prefix")
    console.print("  e.g. 10.1109/ACCESS.2024.123456")
    doi = typer.prompt("DOI", default="")

    console.print("[bold]Notes[/bold] — optional")
    notes = typer.prompt("Notes", default="")

    citation = Citation(
        key=key,
        type=type_str,
        authors=authors,
        title=title,
        year=year,
        venue=venue,
        volume=volume,
        number=number,
        pages=pages,
        doi=doi,
        notes=notes,
    )

    citations_dir.mkdir(parents=True, exist_ok=True)
    with open(cit_path, "w", encoding="utf-8") as f:
        yaml.dump(citation.to_yaml(), f, sort_keys=False, default_flow_style=False, allow_unicode=True)

    authors_display = "; ".join(authors) if authors else "(none)"
    title_display = (title[:70] + "...") if len(title) > 70 else (title or "(none)")
    bibtex_prev = citation.to_bibtex()[:300]

    console.print(
        Panel(
            f"Key:     {key}\n"
            f"Authors: {authors_display}\n"
            f"Title:   {title_display}\n"
            f"Venue:   {venue or '(none)'}\n"
            f"Year:    {year if year is not None else '(none)'}\n"
            f"DOI:     {doi or '(none)'}\n\n"
            f"BibTeX preview:\n{bibtex_prev}\n\n"
            f"Next steps:\n"
            f"  Run `paperforge build` to generate references.bib from this citation data.\n"
            f"  Run `paperforge doctor` to check citation coverage.",
            title="Citation Added",
            border_style="green",
        )
    )
