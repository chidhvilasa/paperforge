from pathlib import Path

import yaml

from paperforge.commands import init
from paperforge.commands.doctor import collect_issues
from paperforge.commands.validate import _extract_all_numbers, _numbers_match_loose
from paperforge.core.project import PaperForgeProject
from paperforge.models.citation import Citation
from paperforge.models.claim import EVIDENCE_CLASSES, Claim


def test_structural_exclusion():
    text = "Figure 1 shows 25 vehicles in Section 3, Table 4, Eq. 5."
    numbers = _extract_all_numbers(text)
    assert len(numbers) == 1
    assert numbers[0][1] == 25.0


def test_scientific_flagging():
    text = "The latency was 73.5%."
    numbers = _extract_all_numbers(text)
    assert len(numbers) == 1
    assert numbers[0][1] == 73.5


def test_numeric_equality():
    assert _numbers_match_loose(0.002, 0.0020, tolerance=1e-4) is True
    assert _numbers_match_loose(0.002, 0.003, tolerance=1e-4) is False
    assert _numbers_match_loose(73.5, 73.5, tolerance=1e-4) is True


def test_citation_evidence():
    cit = Citation(key="test", evidence={"limit": 0.4})
    assert cit.evidence["limit"] == 0.4
    assert not cit.notes


def test_symbolic_exclusion():
    text = "As shown in {{figure:fig1}}, latency drops by 10%."
    numbers = _extract_all_numbers(text)
    assert len(numbers) == 1
    assert numbers[0][1] == 10.0


# --- Evidence-class taxonomy (Critical Safety Principle) ---------------


def _init_project(tmp_path: Path) -> None:
    init.run(tmp_path)


def _write_claim(tmp_path: Path, claim: Claim) -> None:
    path = tmp_path / ".paperforge" / "claims" / f"{claim.id}.yaml"
    path.write_text(yaml.dump(claim.to_yaml()), encoding="utf-8")


def test_evidence_classes_are_the_documented_ten():
    assert EVIDENCE_CLASSES == {
        "AUTHOR_ASSERTED",
        "SOURCE_SUPPORTED",
        "DIRECT_RESULT",
        "DERIVED_RESULT",
        "STATISTICAL_RESULT",
        "INTERPRETATION",
        "HYPOTHESIS",
        "LIMITATION",
        "FUTURE_WORK",
        "PLACEHOLDER",
    }


def test_placeholder_claim_blocks_submission(tmp_path: Path):
    _init_project(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="c_ph",
            text="Placeholder text to be replaced.",
            experiment="exp_01",
            sections=["results"],
            evidence_class="PLACEHOLDER",
        ),
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project, mode="submission")
    assert any(i.code == "EVIDENCE_CLASS_PLACEHOLDER" for i in issues)


def test_placeholder_claim_does_not_block_draft(tmp_path: Path):
    _init_project(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="c_ph2",
            text="Placeholder text to be replaced.",
            experiment="exp_01",
            sections=["results"],
            evidence_class="PLACEHOLDER",
        ),
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project, mode="draft")
    # The finding is still reported (never silently suppressed)...
    assert any(i.code == "EVIDENCE_CLASS_PLACEHOLDER" for i in issues)
    # ...but draft mode's blocking set does not include it (checked at the
    # build layer via DRAFT_BLOCKING, not here) -- this test only verifies
    # collect_issues still surfaces it for visibility in draft mode too.


def test_unsupported_direct_result_blocks_submission(tmp_path: Path):
    _init_project(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="c_unsup",
            text="The system achieves 98% accuracy.",
            experiment="",
            experiments=[],
            citations=[],
            sections=["results"],
            evidence_class="DIRECT_RESULT",
        ),
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project, mode="submission")
    assert any(i.code == "EVIDENCE_CLASS_UNSUPPORTED_RESULT" for i in issues)


def test_direct_result_with_experiment_is_supported(tmp_path: Path):
    _init_project(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="c_sup",
            text="The system achieves 98% accuracy.",
            experiment="exp_01",
            sections=["results"],
            evidence_class="DIRECT_RESULT",
        ),
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project, mode="submission")
    assert not any(i.code == "EVIDENCE_CLASS_UNSUPPORTED_RESULT" for i in issues)


def test_source_supported_result_via_citation_only(tmp_path: Path):
    _init_project(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="c_cited",
            text="Prior work reports similar gains.",
            experiment="",
            experiments=[],
            citations=["smith2024"],
            sections=["related_work"],
            evidence_class="STATISTICAL_RESULT",
        ),
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project, mode="submission")
    assert not any(i.code == "EVIDENCE_CLASS_UNSUPPORTED_RESULT" for i in issues)


def test_interpretation_and_hypothesis_never_require_evidence_link(tmp_path: Path):
    _init_project(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="c_interp",
            text="This suggests the approach generalizes.",
            experiment="",
            experiments=[],
            citations=[],
            sections=["discussion"],
            evidence_class="INTERPRETATION",
        ),
    )
    _write_claim(
        tmp_path,
        Claim(
            id="c_hyp",
            text="We hypothesize this holds at larger scale.",
            experiment="",
            experiments=[],
            citations=[],
            sections=["discussion"],
            evidence_class="HYPOTHESIS",
        ),
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project, mode="submission")
    assert not any(
        i.code == "EVIDENCE_CLASS_UNSUPPORTED_RESULT"
        and i.claim_id in ("c_interp", "c_hyp")
        for i in issues
    )


def test_invalid_evidence_class_is_warning_not_error(tmp_path: Path):
    _init_project(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="c_bad_class",
            text="Some statement.",
            experiment="exp_01",
            sections=["results"],
            evidence_class="NOT_A_REAL_CLASS",
        ),
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project, mode="submission")
    matching = [i for i in issues if i.code == "EVIDENCE_CLASS_INVALID"]
    assert len(matching) == 1
    assert matching[0].severity == "WARNING"


def test_unclassified_claim_is_backward_compatible(tmp_path: Path):
    """A legacy claim with no evidence_class set must not be flagged by
    any of the new checks -- backward compatibility for existing
    projects."""
    _init_project(tmp_path)
    _write_claim(
        tmp_path,
        Claim(
            id="c_legacy",
            text="The system achieves 98% accuracy.",
            experiment="",
            experiments=[],
            citations=[],
            sections=["results"],
        ),
    )
    project = PaperForgeProject.load(tmp_path)
    issues = collect_issues(project, mode="submission")
    assert not any(
        i.code
        in (
            "EVIDENCE_CLASS_PLACEHOLDER",
            "EVIDENCE_CLASS_UNSUPPORTED_RESULT",
            "EVIDENCE_CLASS_INVALID",
        )
        for i in issues
    )
