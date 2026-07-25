"""Tests for paperforge add-claim command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from paperforge.commands import add_claim, init
from paperforge.models.claim import Claim


def _claim_path(tmp_path: Path, claim_id: str) -> Path:
    return tmp_path / ".paperforge" / "claims" / f"{claim_id}.yaml"


def _load_claim(tmp_path: Path, claim_id: str) -> Claim:
    data = yaml.safe_load(_claim_path(tmp_path, claim_id).read_text(encoding="utf-8"))
    return Claim.from_yaml(data)


# Order of prompts in add_claim.run():
# 1. Text, 2. Experiment, 3. Sections, 4. Figures, 5. Tables, 6. Citations, 7. Status


def test_add_claim_creates_claim_file(tmp_path: Path) -> None:
    """add-claim writes a new YAML file to .paperforge/claims/."""
    init.run(tmp_path)
    prompts = [
        "Model achieves 98%.",  # text
        "exp_01",               # experiment
        "results,abstract",     # sections
        "",                     # figures
        "",                     # tables
        "smith2024",            # citations
        "unverified",           # status
    ]
    with patch("typer.prompt", side_effect=prompts):
        add_claim.run(tmp_path)

    assert _claim_path(tmp_path, "claim_02").exists()


def test_add_claim_parses_sections_correctly(tmp_path: Path) -> None:
    """Comma-separated sections are parsed into a list."""
    init.run(tmp_path)
    prompts = [
        "My claim text.",
        "exp_01",
        "results, abstract, discussion",
        "",
        "",
        "",
        "unverified",
    ]
    with patch("typer.prompt", side_effect=prompts):
        add_claim.run(tmp_path)

    claim = _load_claim(tmp_path, "claim_02")
    assert claim.sections == ["results", "abstract", "discussion"]


def test_add_claim_parses_citations_correctly(tmp_path: Path) -> None:
    """Comma-separated citations are parsed into a list."""
    init.run(tmp_path)
    prompts = [
        "My claim text.",
        "exp_01",
        "results",
        "",
        "",
        "smith2024, jones2023",
        "unverified",
    ]
    with patch("typer.prompt", side_effect=prompts):
        add_claim.run(tmp_path)

    claim = _load_claim(tmp_path, "claim_02")
    assert claim.citations == ["smith2024", "jones2023"]


def test_add_claim_empty_figures_gives_empty_list(tmp_path: Path) -> None:
    """Empty figures prompt results in an empty list."""
    init.run(tmp_path)
    prompts = [
        "My claim text.",
        "exp_01",
        "results",
        "",   # figures — empty
        "",
        "",
        "unverified",
    ]
    with patch("typer.prompt", side_effect=prompts):
        add_claim.run(tmp_path)

    claim = _load_claim(tmp_path, "claim_02")
    assert claim.figures == []


def test_add_claim_increments_id_correctly(tmp_path: Path) -> None:
    """add-claim creates claim_04.yaml when claim_01 through claim_03 exist."""
    init.run(tmp_path)
    claims_dir = tmp_path / ".paperforge" / "claims"
    for n in (2, 3):
        (claims_dir / f"claim_{n:02d}.yaml").write_text(
            f"id: claim_{n:02d}\ntext: x\nexperiment: exp_01\nstatus: unverified\n"
            "figures: []\ntables: []\ncitations: []\nsections: []\nlast_verified: null\n",
            encoding="utf-8",
        )

    prompts = [
        "Incremented claim.",
        "exp_01",
        "",
        "",
        "",
        "",
        "unverified",
    ]
    with patch("typer.prompt", side_effect=prompts):
        add_claim.run(tmp_path)

    assert _claim_path(tmp_path, "claim_04").exists()


def test_add_claim_invalid_status_defaults_to_unverified(tmp_path: Path) -> None:
    """Invalid status on two attempts defaults to 'unverified'."""
    init.run(tmp_path)
    prompts = [
        "My claim text.",
        "exp_01",
        "results",
        "",
        "",
        "",
        "invalid_value",   # first attempt — invalid
        "invalid_value",   # second attempt — still invalid → default to unverified
    ]
    with patch("typer.prompt", side_effect=prompts):
        add_claim.run(tmp_path)

    claim = _load_claim(tmp_path, "claim_02")
    assert claim.status == "unverified"


def test_add_claim_fails_without_init(tmp_path: Path) -> None:
    """add-claim exits 1 if the project is not initialized."""
    with pytest.raises(SystemExit) as exc_info:
        add_claim.run(tmp_path)
    assert exc_info.value.code == 1


def test_add_claim_verified_status_accepted(tmp_path: Path) -> None:
    """'verified' is a valid status and is persisted correctly."""
    init.run(tmp_path)
    prompts = [
        "My verified claim.",
        "exp_01",
        "results",
        "",
        "",
        "",
        "verified",
    ]
    with patch("typer.prompt", side_effect=prompts):
        add_claim.run(tmp_path)

    claim = _load_claim(tmp_path, "claim_02")
    assert claim.status == "verified"
