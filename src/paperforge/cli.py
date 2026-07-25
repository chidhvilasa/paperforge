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
