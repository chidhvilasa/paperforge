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


def run(
    project_root: Path,
    key: str | None = None,
    type_str: str | None = None,
    authors: str | None = None,
    title: str | None = None,
    year: int | None = None,
    venue: str | None = None,
    volume: str | None = None,
    number: str | None = None,
    pages: str | None = None,
    doi: str | None = None,
    notes: str | None = None,
    from_yaml: Path | None = None,
) -> None:
    if not (project_root / ".paperforge").exists():
        console.print("[red]Not a PaperForge project. Run `paperforge init` first.[/red]")
        sys.exit(1)

    citations_dir = project_root / ".paperforge" / "citations"
    citations_dir.mkdir(parents=True, exist_ok=True)

    # Handle --from-yaml
    if from_yaml is not None:
        yaml_file = from_yaml if from_yaml.is_absolute() else project_root / from_yaml
        if not yaml_file.exists():
            console.print(f"[red]YAML file not found: {from_yaml}[/red]")
            sys.exit(1)
        data = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
        cit_key = (key or data.get("key") or "").strip()
        if not cit_key:
            console.print("[red]Citation key is required in --from-yaml file or positional argument.[/red]")
            sys.exit(1)

        raw_authors = data.get("authors", [])
        if isinstance(raw_authors, str):
            authors_list = [a.strip() for a in raw_authors.split(";") if a.strip()]
        else:
            authors_list = list(raw_authors)

        type_val = data.get("type", "article")
        valid_type: CitationType = cast(
            CitationType, type_val if type_val in VALID_TYPES else "article"
        )
        citation = Citation(
            key=cit_key,
            type=valid_type,
            authors=authors_list,
            title=data.get("title", ""),
            year=data.get("year"),
            venue=data.get("venue", ""),
            volume=data.get("volume", ""),
            number=data.get("number", ""),
            pages=data.get("pages", ""),
            doi=data.get("doi", ""),
            url=data.get("url", ""),
            publisher=data.get("publisher", ""),
            institution=data.get("institution", ""),
            notes=data.get("notes", ""),
        )
        cit_path = citations_dir / f"{cit_key}.yaml"
        with open(cit_path, "w", encoding="utf-8") as f:
            yaml.dump(
                citation.to_yaml(),
                f,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
            )
        console.print(f"Created {cit_key} from {from_yaml}")
        return

    # Handle Non-interactive flags
    non_interactive = any(
        v is not None
        for v in [
            type_str,
            authors,
            title,
            year,
            venue,
            volume,
            number,
            pages,
            doi,
            notes,
        ]
    )
    if non_interactive:
        if not key:
            console.print("[red]Citation key positional argument is required.[/red]")
            sys.exit(1)
        cit_key = key.strip()
        authors_list = (
            [a.strip() for a in authors.split(";") if a.strip()]
            if authors
            else []
        )
        valid_type_flag: CitationType = cast(
            CitationType,
            type_str.strip().lower()
            if type_str and type_str.strip().lower() in VALID_TYPES
            else "article",
        )
        citation = Citation(
            key=cit_key,
            type=valid_type_flag,
            authors=authors_list,
            title=title or "",
            year=year,
            venue=venue or "",
            volume=volume or "",
            number=number or "",
            pages=pages or "",
            doi=doi or "",
            notes=notes or "",
        )
        cit_path = citations_dir / f"{cit_key}.yaml"
        with open(cit_path, "w", encoding="utf-8") as f:
            yaml.dump(
                citation.to_yaml(),
                f,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
            )
        console.print(f"Created {cit_key}")
        return

    # Interactive mode
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

    cit_path = citations_dir / f"{key}.yaml"
    if cit_path.exists():
        console.print(f"[yellow]Citation '{key}' already exists. Overwriting.[/yellow]")

    console.print("[bold]Type[/bold] — article, inproceedings, book, techreport, misc")
    type_val = typer.prompt("Type", default="article").strip().lower()
    type_str_inp: CitationType = cast(CitationType, type_val if type_val in VALID_TYPES else "article")

    console.print("[bold]Authors[/bold] — comma-separated, Last, First format")
    console.print("  Separate multiple authors with semicolons: Smith, A.; Jones, B.")
    raw_authors = typer.prompt("Authors", default="")
    authors_inp = [a.strip() for a in raw_authors.split(";") if a.strip()]

    console.print("[bold]Title[/bold]")
    title_inp = typer.prompt("Title", default="")

    console.print("[bold]Year[/bold]")
    raw_year = typer.prompt("Year", default="")
    year_inp = int(raw_year) if raw_year.strip().isdigit() else None

    console.print("[bold]Venue[/bold] — journal name, conference name, etc.")
    venue_inp = typer.prompt("Venue", default="")

    console.print("[bold]Volume[/bold] — journal volume number (leave empty if N/A)")
    volume_inp = typer.prompt("Volume", default="")

    console.print("[bold]Issue/Number[/bold] — journal issue (leave empty if N/A)")
    number_inp = typer.prompt("Issue", default="")

    console.print("[bold]Pages[/bold] — e.g. 123--135 or 1-10")
    pages_inp = typer.prompt("Pages", default="")

    console.print("[bold]DOI[/bold] — without https://doi.org/ prefix")
    console.print("  e.g. 10.1109/ACCESS.2024.123456")
    doi_inp = typer.prompt("DOI", default="")

    console.print("[bold]Notes[/bold] — optional")
    notes_inp = typer.prompt("Notes", default="")

    citation = Citation(
        key=key,
        type=type_str_inp,
        authors=authors_inp,
        title=title_inp,
        year=year_inp,
        venue=venue_inp,
        volume=volume_inp,
        number=number_inp,
        pages=pages_inp,
        doi=doi_inp,
        notes=notes_inp,
    )

    with open(cit_path, "w", encoding="utf-8") as f:
        yaml.dump(citation.to_yaml(), f, sort_keys=False, default_flow_style=False, allow_unicode=True)

    authors_display = "; ".join(authors_inp) if authors_inp else "(none)"
    title_display = (title_inp[:70] + "...") if len(title_inp) > 70 else (title_inp or "(none)")
    bibtex_prev = citation.to_bibtex()[:300]

    console.print(
        Panel(
            f"Key:     {key}\n"
            f"Authors: {authors_display}\n"
            f"Title:   {title_display}\n"
            f"Venue:   {venue_inp or '(none)'}\n"
            f"Year:    {year_inp if year_inp is not None else '(none)'}\n"
            f"DOI:     {doi_inp or '(none)'}\n\n"
            f"BibTeX preview:\n{bibtex_prev}\n\n"
            f"Next steps:\n"
            f"  Run `paperforge build` to generate references.bib from this citation data.\n"
            f"  Run `paperforge doctor` to check citation coverage.",
            title="Citation Added",
            border_style="green",
        )
    )
