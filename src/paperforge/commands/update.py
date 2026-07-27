"""paperforge update command."""

from __future__ import annotations

import importlib.metadata
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from rich.console import Console

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def _is_editable_install() -> bool:
    """Check if paperforge-research is installed as editable."""
    try:
        dist = importlib.metadata.distribution("paperforge-research")
        direct_url = dist.read_text("direct_url.json")
        if direct_url:
            data = json.loads(direct_url)
            return data.get("dir_info", {}).get("editable", False)
    except (OSError, KeyError, json.JSONDecodeError, AttributeError, importlib.metadata.PackageNotFoundError):
        pass
    return False


def run(pre: bool = False, git: bool = False) -> None:
    if git:
        possible = [
            Path.home() / "Downloads" / "PaperForge" / "paperforge",
            Path.cwd(),
            Path.cwd().parent,
        ]
        repo = None
        for p in possible:
            if (p / "pyproject.toml").exists():
                content = (p / "pyproject.toml").read_text(encoding="utf-8")
                if "paperforge-research" in content:
                    repo = p
                    break

        if repo is None:
            console.print(
                "[red]Could not find paperforge repo. "
                "Run from the repo directory.[/red]"
            )
            return

        console.print(f"Updating from repo: {repo}")
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            capture_output=True,
            text=True,
            cwd=repo,
            check=False,
        )
        console.print(result.stdout)
        if result.returncode == 0:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", ".", "--quiet"],
                cwd=repo,
                check=False,
            )
            console.print("[green]Git update complete.[/green]")
        else:
            console.print(f"[red]Git pull failed:[/red] {result.stderr}")
        return

    if _is_editable_install():
        console.print(
            "[yellow]PaperForge is installed in editable/development mode.[/yellow]"
        )
        console.print("To update a development install, pull the latest changes:")
        console.print("  cd <paperforge-repo>")
        console.print("  git pull origin main")
        console.print("  pip install -e . --quiet")
        console.print("Or run: paperforge update --git")
        return

    try:
        current = importlib.metadata.version("paperforge-research")
    except importlib.metadata.PackageNotFoundError:
        current = "unknown"
    except Exception:  # noqa: BLE001
        current = "unknown"

    console.print(f"Current version: paperforge-research {current}")

    try:
        url = "https://pypi.org/pypi/paperforge-research/json"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
        latest = data["info"]["version"]
        console.print(f"Latest version:  paperforge-research {latest}")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        console.print(
            "[yellow]Could not check PyPI: connection or format error[/yellow]"
        )
        console.print("Run manually: pip install paperforge-research --upgrade")
        return
    except Exception as e:  # noqa: BLE001
        console.print(f"[yellow]Could not check PyPI: {e}[/yellow]")
        console.print("Run manually: pip install paperforge-research --upgrade")
        return

    try:
        from packaging.version import Version

        already_latest = (
            Version(current) >= Version(latest)
            if current != "unknown"
            else False
        )
    except Exception:  # noqa: BLE001
        already_latest = current == latest

    if already_latest and not pre:
        console.print("[green]Already up to date.[/green]")
        return

    console.print(f"Upgrading {current} → {latest}...")

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "paperforge-research",
        "--upgrade",
        "--quiet",
    ]
    if pre:
        cmd.append("--pre")

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode == 0:
        console.print(
            f"[green]Updated to paperforge-research {latest}[/green]"
        )
        console.print(
            "[yellow]Restart your terminal or re-run 'paperforge' "
            "for the new version to take effect.[/yellow]"
        )
    else:
        console.print("[red]Update failed:[/red]")
        console.print(result.stderr)
        console.print(
            "Try manually: pip install paperforge-research --upgrade"
        )
