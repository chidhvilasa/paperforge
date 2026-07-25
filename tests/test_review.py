"""Tests for the paperforge review command."""

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest
import yaml

from paperforge.commands import init, review
from paperforge.models.claim import Claim
from paperforge.models.experiment import Experiment


def _make_valid_project(tmp_path: Path) -> None:
    init.run(tmp_path)

    claim_path = tmp_path / ".paperforge" / "claims" / "claim_01.yaml"
    claim = Claim(
        id="claim_01",
        text="This model achieves 98.4% accuracy.",
        experiment="exp_01",
        sections=["results"],
        status="verified",
    )
    claim_path.write_text(
        yaml.dump(claim.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    exp_path = tmp_path / ".paperforge" / "experiments" / "exp_01.yaml"
    experiment = Experiment(id="exp_01", metrics={"accuracy": 98.4})
    exp_path.write_text(
        yaml.dump(experiment.to_yaml(), default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    paper_yaml = tmp_path / ".paperforge" / "paper.yaml"
    data = yaml.safe_load(paper_yaml.read_text(encoding="utf-8"))
    data["title"] = "Test Paper"
    data["authors"] = ["Test Author"]
    paper_yaml.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def test_review_fails_without_init(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        review.run(tmp_path, model=None)
    assert exc_info.value.code == 1


def test_review_blocked_by_errors(tmp_path: Path) -> None:
    init.run(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        review.run(tmp_path, model=None)
    assert exc_info.value.code == 1


def test_review_fails_if_llm_not_found(tmp_path: Path) -> None:
    _make_valid_project(tmp_path)

    with (
        patch("paperforge.commands.review.shutil.which", return_value=None),
        pytest.raises(SystemExit) as exc_info,
    ):
        review.run(tmp_path, model=None)
    assert exc_info.value.code == 1


def test_review_calls_llm_subprocess(tmp_path: Path) -> None:
    _make_valid_project(tmp_path)

    with (
        patch(
            "paperforge.commands.review.shutil.which", return_value="/usr/bin/llm"
        ),
        patch(
            "paperforge.commands.review.subprocess.run",
            return_value=CompletedProcess(
                args=[], returncode=0, stdout="Good paper.", stderr=""
            ),
        ) as mock_run,
    ):
        review.run(tmp_path, model=None)

    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "llm" in call_args


def test_review_passes_model_flag(tmp_path: Path) -> None:
    _make_valid_project(tmp_path)

    with (
        patch(
            "paperforge.commands.review.shutil.which", return_value="/usr/bin/llm"
        ),
        patch(
            "paperforge.commands.review.subprocess.run",
            return_value=CompletedProcess(
                args=[], returncode=0, stdout="Good paper.", stderr=""
            ),
        ) as mock_run,
    ):
        review.run(tmp_path, model="gpt-4o")

    call_args = mock_run.call_args[0][0]
    assert "-m" in call_args
    assert "gpt-4o" in call_args


def test_review_saves_output_file(tmp_path: Path) -> None:
    _make_valid_project(tmp_path)

    with (
        patch(
            "paperforge.commands.review.shutil.which", return_value="/usr/bin/llm"
        ),
        patch(
            "paperforge.commands.review.subprocess.run",
            return_value=CompletedProcess(
                args=[], returncode=0, stdout="Review text.", stderr=""
            ),
        ),
    ):
        review.run(tmp_path, model=None)

    assert (tmp_path / ".paperforge" / "review" / "latest_review.md").exists()


def test_review_output_contains_advisory_warning(tmp_path: Path) -> None:
    _make_valid_project(tmp_path)

    with (
        patch(
            "paperforge.commands.review.shutil.which", return_value="/usr/bin/llm"
        ),
        patch(
            "paperforge.commands.review.subprocess.run",
            return_value=CompletedProcess(
                args=[], returncode=0, stdout="Review text.", stderr=""
            ),
        ),
    ):
        review.run(tmp_path, model=None)

    content = (
        tmp_path / ".paperforge" / "review" / "latest_review.md"
    ).read_text(encoding="utf-8")
    assert "advisory" in content.lower()


def test_review_exits_on_llm_failure(tmp_path: Path) -> None:
    _make_valid_project(tmp_path)

    with (
        patch(
            "paperforge.commands.review.shutil.which", return_value="/usr/bin/llm"
        ),
        patch(
            "paperforge.commands.review.subprocess.run",
            return_value=CompletedProcess(
                args=[], returncode=1, stdout="", stderr="API error"
            ),
        ),
        pytest.raises(SystemExit) as exc_info,
    ):
        review.run(tmp_path, model=None)
    assert exc_info.value.code == 1
