"""PaperForge command-line interface."""

from pathlib import Path

import typer

from paperforge import __version__

app = typer.Typer(
    name="paperforge",
    help="A research dependency engine that tracks the graph between "
    "experiments and scientific claims.",
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"paperforge {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version_flag: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the paperforge version and exit.",
    ),
) -> None:
    """PaperForge: a research dependency engine."""


@app.command()
def init(
    path: Path = typer.Argument(
        default=Path("."),
        help="Directory to initialize. Defaults to current directory.",
    ),
) -> None:
    """Initialize PaperForge in a research project directory."""
    from paperforge.commands.init import run

    run(path.resolve())


@app.command()
def inspect(
    path: Path = typer.Argument(
        default=Path("."),
        help="Directory to inspect. Defaults to current directory.",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of a console panel."
    ),
) -> None:
    """Read-only reconnaissance of a directory before intake or import.

    Detects existing manuscripts, bibliography, figures, tables,
    notebooks, data files, venue template files, package managers, Git
    state, likely secrets, and absolute local paths. Never modifies or
    executes anything it finds.
    """
    from paperforge.commands.inspect import run

    run(project_root=path.resolve(), json_output=json_output)


manifest_app = typer.Typer(
    name="manifest",
    help="Work with the canonical paperforge.project.yaml manifest.",
)
app.add_typer(manifest_app, name="manifest")


@manifest_app.command("schema")
def manifest_schema(
    output: Path | None = typer.Option(
        None, "--output", help="Write the JSON Schema document to this path."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Wrap the schema in the standard JSON result envelope."
    ),
) -> None:
    """Print (or save) the JSON Schema for paperforge.project.yaml."""
    from paperforge.commands.manifest_cmd import run_schema

    raise typer.Exit(code=run_schema(output=output, json_output=json_output))


@manifest_app.command("validate")
def manifest_validate(
    path: Path = typer.Argument(
        default=Path("paperforge.project.yaml"), help="Path to the manifest file."
    ),
    mode: str = typer.Option(
        "draft", "--mode", "-m", help="Validation mode: draft, review, or submission."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Validate a manifest file (safe YAML, structure, unknown fields)."""
    from paperforge.commands.manifest_cmd import run_validate

    raise typer.Exit(
        code=run_validate(path.resolve(), mode=mode, json_output=json_output)
    )


@manifest_app.command("migrate")
def manifest_migrate(
    input_path: Path = typer.Option(
        Path("paperforge.project.yaml"), "--input", help="Manifest file to migrate."
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Write the migrated manifest here instead of overwriting --input.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Report what would change without writing."
    ),
    yes: bool = typer.Option(
        False, "--yes", help="Do not prompt before overwriting in place."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Migrate a manifest to the current schema version."""
    from paperforge.commands.manifest_cmd import run_migrate

    raise typer.Exit(
        code=run_migrate(
            input_path=input_path.resolve(),
            output_path=output.resolve() if output else None,
            dry_run=dry_run,
            yes=yes,
            json_output=json_output,
        )
    )


@app.command()
def requirements(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    manifest: Path | None = typer.Option(
        None,
        "--manifest",
        help="Manifest path. Defaults to <path>/paperforge.project.yaml.",
    ),
    mode: str = typer.Option(
        "draft", "--mode", "-m", help="outline, draft, review, or submission."
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Directory to write reports to. Defaults to <path>/.paperforge.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Evaluate mode-aware manuscript requirements against the project manifest."""
    from paperforge.commands.requirements_cmd import run as run_requirements

    root = path.resolve()
    raise typer.Exit(
        code=run_requirements(
            project_root=root,
            manifest_path=manifest.resolve() if manifest else None,
            mode=mode,
            json_output=json_output,
            output_dir=output.resolve() if output else None,
        )
    )


@app.command()
def plan(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    manifest: Path | None = typer.Option(
        None,
        "--manifest",
        help="Manifest path. Defaults to <path>/paperforge.project.yaml.",
    ),
    section: str | None = typer.Option(
        None, "--section", help="Show only this section."
    ),
    refresh: bool = typer.Option(
        False,
        "--refresh",
        help="No-op: the plan is always rebuilt fresh from the current manifest.",
    ),
    approve: bool = typer.Option(
        False, "--approve", help="Record approval of the current plan."
    ),
    revoke_approval: bool = typer.Option(
        False, "--revoke-approval", help="Revoke any existing approval."
    ),
    mode: str = typer.Option(
        "submission", "--mode", "-m", help="Mode the approval is recorded for."
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Do not prompt; approver is recorded as 'agent'.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Build a structural, approval-gated generation plan (no manuscript prose)."""
    from paperforge.commands.plan_cmd import run as run_plan

    _ = refresh
    raise typer.Exit(
        code=run_plan(
            project_root=path.resolve(),
            manifest_path=manifest.resolve() if manifest else None,
            section=section,
            approve=approve,
            revoke_approval=revoke_approval,
            mode=mode,
            json_output=json_output,
            non_interactive=non_interactive,
        )
    )


@app.command()
def generate(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    manifest: Path | None = typer.Option(
        None,
        "--manifest",
        help="Manifest path. Defaults to <path>/paperforge.project.yaml.",
    ),
    all_sections: bool = typer.Option(
        True, "--all/--not-all", help="Generate every planned section (default)."
    ),
    section: str | None = typer.Option(
        None, "--section", help="Generate only this section."
    ),
    regenerate: str | None = typer.Option(
        None, "--regenerate", help="Regenerate only this section."
    ),
    outline_only: bool = typer.Option(
        False,
        "--outline-only",
        help="Structural outline only (headings/goals/permitted claims). No prose, no approval required.",
    ),
    draft_with_placeholders: bool = typer.Option(
        False,
        "--draft-with-placeholders",
        help="Watermarked draft including placeholder claims. No approval required. Fails submission mode.",
    ),
    no_ai: bool = typer.Option(
        True,
        "--no-ai/--ai",
        help="Use the deterministic no-AI provider (default; the only provider that ships).",
    ),
    provider: str = typer.Option(
        "no_ai", "--provider", help="Generation provider: no_ai or fixture."
    ),
    review_existing: bool = typer.Option(
        False,
        "--review-existing",
        help="List already-generated sections instead of generating.",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Never prompt (this command never prompts regardless).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Deterministically generate manuscript section content from an approved plan."""
    from paperforge.commands.generate_cmd import run as run_generate

    _ = all_sections  # generating "all" planned sections is the default when no --section/--regenerate given
    effective_provider = provider if provider != "no_ai" or no_ai else "no_ai"
    raise typer.Exit(
        code=run_generate(
            project_root=path.resolve(),
            manifest_path=manifest.resolve() if manifest else None,
            section=section,
            regenerate=regenerate,
            outline_only=outline_only,
            draft_with_placeholders=draft_with_placeholders,
            provider_name=effective_provider,
            review_existing=review_existing,
            non_interactive=non_interactive,
            json_output=json_output,
        )
    )


provenance_app = typer.Typer(
    name="provenance", help="Inspect and validate generation provenance sidecars."
)
app.add_typer(provenance_app, name="provenance")


@provenance_app.command("show")
def provenance_show(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Show recorded provenance for generated sections."""
    from paperforge.commands.provenance_cmd import run_show

    raise typer.Exit(
        code=run_show(project_root=path.resolve(), json_output=json_output)
    )


@provenance_app.command("validate")
def provenance_validate(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    manifest: Path | None = typer.Option(None, "--manifest", help="Manifest path."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Validate provenance: staleness, missing claims/evidence, unreviewed results, placeholders."""
    from paperforge.commands.provenance_cmd import run_validate

    raise typer.Exit(
        code=run_validate(
            project_root=path.resolve(),
            manifest_path=manifest.resolve() if manifest else None,
            json_output=json_output,
        )
    )


@provenance_app.command("export")
def provenance_export(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    output: Path | None = typer.Option(
        None, "--output", help="Write exported provenance JSON here."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Export the full provenance index and records as JSON."""
    from paperforge.commands.provenance_cmd import run_export

    raise typer.Exit(
        code=run_export(
            project_root=path.resolve(),
            output=output.resolve() if output else None,
            json_output=json_output,
        )
    )


@app.command()
def capture(
    results: Path = typer.Argument(..., help="Path to metrics JSON file."),
    experiment: str = typer.Option(
        ..., "--experiment", "-e", help="Experiment ID, e.g. exp_27"
    ),
    path: Path = typer.Option(
        Path("."), "--path", "-p", help="Project root. Defaults to current directory."
    ),
) -> None:
    """Capture experiment results and create a draft claim."""
    from paperforge.commands.capture import run

    run(
        results=results.resolve(), experiment_id=experiment, project_root=path.resolve()
    )


@app.command()
def doctor(
    path: Path = typer.Option(
        Path("."), "--path", "-p", help="Project root. Defaults to current directory."
    ),
    fix: bool = typer.Option(False, "--fix", help="Auto-resolve fixable warnings."),
    target: str | None = typer.Option(
        None,
        "--target",
        "-t",
        help="Venue target for additional checks: ieee, acm, neurips",
    ),
    self_check: bool = typer.Option(
        False, "--self-check", help="Check PaperForge installation health."
    ),
    pre_submission: bool = typer.Option(
        False, "--pre-submission", help="Run full submission readiness report."
    ),
    fix_hints: bool = typer.Option(
        False, "--fix-hints", help="Show concrete fix suggestions for each issue."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output issues as JSON for tooling integration."
    ),
) -> None:
    """Check research project consistency."""
    from paperforge.commands.doctor import run

    run(
        project_root=path.resolve(),
        fix=fix,
        target=target,
        self_check=self_check,
        pre_submission=pre_submission,
        fix_hints=fix_hints,
        json_output=json_output,
    )


@app.command()
def impact(
    experiment_id: str = typer.Argument(..., help="Experiment ID, e.g. exp_27"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
) -> None:
    """Show everything affected by a change to an experiment."""
    from paperforge.commands.impact import run

    run(experiment_id=experiment_id, project_root=path.resolve())


@app.command()
def build(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    target: str = typer.Option(
        "ieee", "--target", "-t", help="Venue target: ieee, acm, neurips"
    ),
    no_reveal: bool = typer.Option(
        False, "--no-reveal", help="Do not open output folder after build."
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force rebuild even if PDF is up to date."
    ),
    force_anyway: bool = typer.Option(
        False,
        "--force-anyway",
        help="Build even if doctor checks fail. NOT recommended for submission.",
    ),
    mode: str = typer.Option(
        "draft",
        "--mode",
        "-m",
        help="Build mode: draft or submission. Submission mode blocks on all P0 failures.",
    ),
) -> None:
    """Compile research data into an IEEE LaTeX paper."""
    from paperforge.commands.build import run

    run(
        project_root=path.resolve(),
        target=target,
        no_reveal=no_reveal,
        force=force,
        force_anyway=force_anyway,
        mode=mode,
    )


@app.command()
def review(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="llm model to use, e.g. gpt-4o. Uses llm default if omitted.",
    ),
) -> None:
    """AI-assisted paper review. Advisory only."""
    from paperforge.commands.review import run

    run(project_root=path.resolve(), model=model)


@app.command()
def improve(
    claim_id: str | None = typer.Argument(
        None,
        help="Specific claim ID to improve, e.g. claim_01",
    ),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="llm model to use. Uses llm default if omitted.",
    ),
    all_claims: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Improve all unverified claims.",
    ),
) -> None:
    """AI-assisted claim improvement. Suggests edits, never auto-applies."""
    from paperforge.commands.improve import run

    run(
        project_root=path.resolve(),
        claim_id=claim_id,
        model=model,
        all_claims=all_claims,
    )


@app.command(name="add-claim")
def add_claim(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    text: str | None = typer.Option(
        None, "--text", "-t", help="Claim text (non-interactive)"
    ),
    experiment: str | None = typer.Option(
        None, "--experiment", "-e", help="Experiment ID"
    ),
    sections: str | None = typer.Option(
        None,
        "--sections",
        "-s",
        help="Comma-separated section list, e.g. results,abstract",
    ),
    figures: str | None = typer.Option(
        None, "--figures", help="Comma-separated figure IDs, e.g. fig_01,fig_02"
    ),
    tables: str | None = typer.Option(
        None, "--tables", help="Comma-separated table IDs, e.g. tbl_01"
    ),
    citations: str | None = typer.Option(
        None,
        "--citations",
        "-c",
        help="Comma-separated BibTeX keys, e.g. smith2024,jones2023",
    ),
    status: str | None = typer.Option(
        None, "--status", help="Claim status: verified, unverified, stale"
    ),
    from_yaml: Path | None = typer.Option(
        None, "--from-yaml", help="Path to YAML file to import claim from"
    ),
) -> None:
    """Interactively create or script a new claim linked to an experiment."""
    from paperforge.commands.add_claim import run

    run(
        project_root=path.resolve(),
        text=text,
        experiment=experiment,
        sections=sections,
        figures=figures,
        tables=tables,
        citations=citations,
        status=status,
        from_yaml=from_yaml,
    )


@app.command(name="add-figure")
def add_figure(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    caption: str | None = typer.Option(None, "--caption", help="Figure caption"),
    fig_path: str | None = typer.Option(
        None, "--path-file", help="Relative path to image file, e.g. figures/fig_01.png"
    ),
    format: str | None = typer.Option(
        None, "--format", help="Image format: png, pdf, eps, svg"
    ),
    width: float | None = typer.Option(
        None, "--width", help="Intended LaTeX width in inches, e.g. 3.5"
    ),
    dpi: int | None = typer.Option(None, "--dpi", help="Resolution DPI, e.g. 300"),
    section: str | None = typer.Option(
        None, "--section", help="First mentioned in section"
    ),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes"),
    wide: bool = typer.Option(
        False, "--wide", help="Spans both columns in IEEE layout"
    ),
    from_yaml: Path | None = typer.Option(
        None, "--from-yaml", help="Path to YAML file to import figure from"
    ),
) -> None:
    """Interactively create or script a new figure YAML file."""
    from paperforge.commands.add_figure import run

    run(
        project_root=path.resolve(),
        caption=caption,
        path=fig_path,
        format=format,
        width=width,
        dpi=dpi,
        section=section,
        notes=notes,
        wide=wide,
        from_yaml=from_yaml,
    )


@app.command(name="generate-figures")
def generate_figures(
    figure_id: str | None = typer.Argument(
        None, help="Specific figure ID, or all if omitted"
    ),
    path: Path = typer.Option(Path("."), "--path", "-p"),
) -> None:
    """Generate matplotlib figures from experiment data."""
    from paperforge.commands.generate_figures import run

    run(project_root=path.resolve(), figure_id=figure_id)


@app.command(name="add-table")
def add_table(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    caption: str | None = typer.Option(None, "--caption", help="Table caption"),
    experiment: str | None = typer.Option(
        None, "--experiment", "-e", help="Source experiment ID"
    ),
    columns: str | None = typer.Option(
        None, "--columns", help="Comma-separated column headers"
    ),
    section: str | None = typer.Option(
        None, "--section", help="First mentioned in section"
    ),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes"),
    wide: bool = typer.Option(
        False, "--wide", help="Spans both columns in IEEE layout"
    ),
    from_yaml: Path | None = typer.Option(
        None, "--from-yaml", help="Path to YAML file to import table from"
    ),
) -> None:
    """Interactively create or script a new table YAML file."""
    from paperforge.commands.add_table import run

    run(
        project_root=path.resolve(),
        caption=caption,
        experiment=experiment,
        columns=columns,
        section=section,
        notes=notes,
        wide=wide,
        from_yaml=from_yaml,
    )


@app.command(name="add-citation")
def add_citation(
    key: str | None = typer.Argument(
        None,
        help="BibTeX key, e.g. smith2024. Prompted if omitted.",
    ),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    type_str: str | None = typer.Option(
        None, "--type", help="Citation type: article, inproceedings, book, etc."
    ),
    authors: str | None = typer.Option(
        None,
        "--authors",
        help="Semicolon-separated author list, e.g. Smith, A.; Jones, B.",
    ),
    title: str | None = typer.Option(None, "--title", help="Publication title"),
    year: int | None = typer.Option(None, "--year", help="Publication year"),
    venue: str | None = typer.Option(None, "--venue", help="Venue or journal name"),
    volume: str | None = typer.Option(None, "--volume", help="Volume number"),
    number: str | None = typer.Option(None, "--number", help="Issue or number"),
    pages: str | None = typer.Option(None, "--pages", help="Page range, e.g. 123--135"),
    doi: str | None = typer.Option(
        None, "--doi", help="DOI without https://doi.org/ prefix"
    ),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes"),
    from_yaml: Path | None = typer.Option(
        None, "--from-yaml", help="Path to YAML file to import citation from"
    ),
) -> None:
    """Interactively add or script citation metadata for a BibTeX key."""
    from paperforge.commands.add_citation import run

    run(
        project_root=path.resolve(),
        key=key,
        type_str=type_str,
        authors=authors,
        title=title,
        year=year,
        venue=venue,
        volume=volume,
        number=number,
        pages=pages,
        doi=doi,
        notes=notes,
        from_yaml=from_yaml,
    )


@app.command(name="import")
def import_content(
    section: str | None = typer.Argument(
        None, help="Section to import, e.g. 'abstract'. All if omitted."
    ),
    path: Path = typer.Option(Path("."), "--path", "-p"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing claims with same text."
    ),
) -> None:
    """Import content from paper_information/ into .paperforge/."""
    from paperforge.commands.import_content import run

    run(project_root=path.resolve(), section=section, force=force)


@app.command(name="install-hooks")
def install_hooks(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    uninstall: bool = typer.Option(False, "--uninstall", help="Remove the hook."),
) -> None:
    """Install a git pre-commit hook that runs paperforge doctor."""
    from paperforge.commands.install_hooks import run

    run(project_root=path.resolve(), uninstall=uninstall)


@app.command()
def export(
    fmt: str = typer.Argument(
        "json", help="Format: bibtex, json, markdown, traceability, overleaf"
    ),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path or directory. Defaults to .paperforge/output/.",
    ),
) -> None:
    """Export research graph as BibTeX, JSON, Markdown, Traceability Matrix, or Overleaf zip."""
    from paperforge.commands.export import run

    run(
        project_root=path.resolve(),
        fmt=fmt,
        output=output.resolve() if output else None,
    )


@app.command()
def status(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
) -> None:
    """Show project health dashboard."""
    from paperforge.commands.status import run

    run(project_root=path.resolve())


@app.command()
def find(
    query: str = typer.Argument(..., help="Search term."),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    field: str = typer.Option(
        "all",
        "--field",
        "-f",
        help="Search scope: claims, experiments, all",
    ),
) -> None:
    """Search claims and experiments by keyword."""
    from paperforge.commands.find import run

    run(query=query, project_root=path.resolve(), field=field)


@app.command(name="log")
def log_cmd(
    claim_id: str = typer.Argument(..., help="Claim ID, e.g. claim_01"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    limit: int = typer.Option(
        10, "--limit", "-n", help="Maximum number of history entries to show."
    ),
) -> None:
    """Show change history for a claim."""
    from paperforge.commands.log_cmd import run

    run(claim_id=claim_id, project_root=path.resolve(), limit=limit)


@app.command()
def diff(
    claim_id: str = typer.Argument(..., help="Claim ID, e.g. claim_01"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    against: str = typer.Option(
        "previous",
        "--against",
        "-a",
        help="Diff target: previous, HEAD~1, experiment",
    ),
) -> None:
    """Show what changed in a claim vs its history or linked experiment."""
    from paperforge.commands.diff import run

    run(claim_id=claim_id, project_root=path.resolve(), against=against)


@app.command()
def venues() -> None:
    """List available venue targets for --target option."""
    from rich.console import Console
    from rich.table import Table

    from paperforge.venues.registry import get_plugin, list_plugins

    console = Console()
    table = Table(title="Available Venue Targets")
    table.add_column("Target", style="cyan")
    table.add_column("Display Name")
    table.add_column("Document Class")
    table.add_column("Page Limit")
    for name in list_plugins():
        plugin = get_plugin(name)
        table.add_row(
            plugin.name,
            plugin.display_name,
            plugin.latex_documentclass[:40] + "...",
            str(plugin.max_pages) if plugin.max_pages else "None",
        )
    console.print(table)


@app.command()
def update(
    pre: bool = typer.Option(False, "--pre", help="Include pre-release versions."),
    git: bool = typer.Option(
        False, "--git", help="Update from git (for development installs)."
    ),
) -> None:
    """Update paperforge-research to the latest version."""
    from paperforge.commands.update import run

    run(pre=pre, git=git)


@app.command()
def sync(
    direction: str = typer.Option(
        "status",
        "--direction",
        "-d",
        help="Sync direction: to-md, to-claims, or status",
    ),
    path: Path = typer.Option(Path("."), "--path", "-p"),
    force: bool = typer.Option(False, "--force", "-f"),
) -> None:
    """Sync between paper_information/ and .paperforge/ (bidirectional)."""
    from paperforge.commands.sync import run

    run(project_root=path.resolve(), direction=direction, force=force)


@app.command()
def validate(
    path: Path = typer.Option(Path("."), "--path", "-p"),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output path for VALIDATION_LOG.md"
    ),
) -> None:
    """Validate all numerical claims against experiment data."""
    from paperforge.commands.validate import run

    run(project_root=path.resolve(), output=output)


@app.command()
def clean(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
) -> None:
    """Remove stale build artifacts and LaTeX aux files."""
    from paperforge.commands.clean import run

    run(project_root=path.resolve())


@app.command()
def preflight(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    mode: str = typer.Option(
        "draft", "--mode", "-m", help="Build mode: draft or submission."
    ),
    pdf: Path | None = typer.Option(None, "--pdf", help="Custom PDF path to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
    open_renders: bool = typer.Option(
        False, "--open-renders", help="Open rendered page images folder."
    ),
) -> None:
    """Run rendered PDF preflight, template fingerprinting, visual overlap & structural checks."""
    from paperforge.commands.preflight import run

    run(
        project_root=path.resolve(),
        mode=mode,
        pdf_path=pdf,
        json_output=json_output,
        open_renders=open_renders,
    )


@app.command()
def references(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    online: bool = typer.Option(
        False, "--online", help="Verify DOIs against Crossref API."
    ),
) -> None:
    """Verify BibTeX reference metadata and optionally check DOIs against Crossref."""
    from paperforge.core.project import PaperForgeProject
    from paperforge.services.reference_verifier import verify_references

    project = PaperForgeProject.load(path.resolve())
    reports_dir = (
        project.output_dir.parent.parent / "reports"
        if project.output_dir.parent.name == "paper_generated"
        else project.output_dir / "reports"
    )
    reports_dir.mkdir(parents=True, exist_ok=True)

    rep = verify_references(project, reports_dir, online=online)
    typer.echo(
        f"Reference verification complete. Checked {rep.total_citations} references "
        f"(online verified: {rep.online_verified_count}). Status: {'PASSED' if rep.passed else 'ISSUES FOUND'}"
    )


if __name__ == "__main__":
    app()
