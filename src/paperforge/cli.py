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
    fix: bool = typer.Option(
        False, "--fix", help="Auto-resolve fixable warnings."
    ),
    target: str | None = typer.Option(
        None,
        "--target",
        "-t",
        help="Venue target for additional checks: ieee, acm, neurips",
    ),
) -> None:
    """Check research project consistency."""
    from paperforge.commands.doctor import run

    run(project_root=path.resolve(), fix=fix, target=target)


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
) -> None:
    """Compile research data into an IEEE LaTeX paper."""
    from paperforge.commands.build import run

    run(project_root=path.resolve(), target=target, no_reveal=no_reveal)


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
    path: Path = typer.Option(
        Path("."), "--path", "-p", help="Project root."
    ),
    model: str | None = typer.Option(
        None, "--model", "-m",
        help="llm model to use. Uses llm default if omitted.",
    ),
    all_claims: bool = typer.Option(
        False, "--all", "-a",
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
) -> None:
    """Interactively create a new claim linked to an experiment."""
    from paperforge.commands.add_claim import run

    run(project_root=path.resolve())


@app.command(name="add-figure")
def add_figure(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
) -> None:
    """Interactively create a new figure YAML file."""
    from paperforge.commands.add_figure import run

    run(project_root=path.resolve())


@app.command(name="add-table")
def add_table(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
) -> None:
    """Interactively create a new table YAML file."""
    from paperforge.commands.add_table import run

    run(project_root=path.resolve())


@app.command(name="add-citation")
def add_citation(
    key: str | None = typer.Argument(
        None,
        help="BibTeX key, e.g. smith2024. Prompted if omitted.",
    ),
    path: Path = typer.Option(
        Path("."), "--path", "-p", help="Project root."
    ),
) -> None:
    """Interactively add citation metadata for a BibTeX key."""
    from paperforge.commands.add_citation import run

    run(project_root=path.resolve(), key=key)


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
    fmt: str = typer.Argument("json", help="Format: bibtex, json, markdown, traceability"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path or directory. Defaults to .paperforge/output/.",
    ),
) -> None:
    """Export research graph as BibTeX, JSON, Markdown, or Traceability Matrix."""
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
