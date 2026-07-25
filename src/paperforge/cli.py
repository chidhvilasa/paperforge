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
) -> None:
    """Check research project consistency."""
    from paperforge.commands.doctor import run

    run(project_root=path.resolve(), fix=fix)
