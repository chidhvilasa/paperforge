"""paperforge update command."""

from __future__ import annotations

import importlib.metadata
import json
import subprocess
import sys
import urllib.error
import urllib.request

from rich.console import Console

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def run(pre: bool = False) -> None:
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
        console.print("[yellow]Could not check PyPI: connection or format error[/yellow]")
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
