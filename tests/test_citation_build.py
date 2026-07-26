from pathlib import Path

from paperforge.commands.build import run as run_build


def test_bibtex_generated_from_yaml_not_stub(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "claims").mkdir(parents=True)
    (pf_dir / "experiments").mkdir(parents=True)
    (pf_dir / "citations").mkdir(parents=True)

    (pf_dir / "paper.yaml").write_text(
        "title: Test\nauthors: [A]\nsections: [results]\nacknowledgment: Thanks\nbuild:\n  output_dir: 'paper'\n",
        encoding="utf-8",
    )
    (pf_dir / "experiments" / "exp_01.yaml").write_text(
        "id: exp_01\ndescription: D\nmetrics: {acc: 90}\nhardware: H\ndataset: D\nseed: 42\nresults_file: r.json\n",
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: Claim 90% acc\nexperiment: exp_01\nsections: [results]\ncitations: [smith2024]\nstatus: verified\n",
        encoding="utf-8",
    )
    (pf_dir / "citations" / "smith2024.yaml").write_text(
        "key: smith2024\ntitle: Real Title Paper\ntype: article\nauthors: [Smith, A.]\nyear: 2024\n",
        encoding="utf-8",
    )

    run_build(tmp_path, no_reveal=True)
    bib_content = (tmp_path / "paper" / "references.bib").read_text(encoding="utf-8")
    assert "TODO" not in bib_content
    assert "Real Title Paper" in bib_content


def test_mixed_citations_real_and_stub(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "claims").mkdir(parents=True)
    (pf_dir / "experiments").mkdir(parents=True)
    (pf_dir / "citations").mkdir(parents=True)

    (pf_dir / "paper.yaml").write_text(
        "title: Test\nauthors: [A]\nsections: [results]\nacknowledgment: Thanks\nbuild:\n  output_dir: 'paper'\n",
        encoding="utf-8",
    )
    (pf_dir / "experiments" / "exp_01.yaml").write_text(
        "id: exp_01\ndescription: D\nmetrics: {acc: 90}\nhardware: H\ndataset: D\nseed: 42\nresults_file: r.json\n",
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: Claim 90% acc\nexperiment: exp_01\nsections: [results]\ncitations: [smith2024, jones2023]\nstatus: verified\n",
        encoding="utf-8",
    )
    (pf_dir / "citations" / "smith2024.yaml").write_text(
        "key: smith2024\ntitle: Real Title Paper\ntype: article\nauthors: [Smith, A.]\nyear: 2024\n",
        encoding="utf-8",
    )

    run_build(tmp_path, no_reveal=True)
    bib_content = (tmp_path / "paper" / "references.bib").read_text(encoding="utf-8")
    blocks = bib_content.split("@")
    smith_block = next(b for b in blocks if b.startswith("article{smith2024"))
    jones_block = next(b for b in blocks if b.startswith("article{jones2023"))

    assert "TODO" not in smith_block
    assert "TODO" in jones_block


def test_citation_yaml_as_source_of_truth(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "claims").mkdir(parents=True)
    (pf_dir / "experiments").mkdir(parents=True)
    (pf_dir / "citations").mkdir(parents=True)

    (pf_dir / "paper.yaml").write_text(
        "title: Test\nauthors: [A]\nsections: [results]\nacknowledgment: Thanks\nbuild:\n  output_dir: 'paper'\n",
        encoding="utf-8",
    )
    (pf_dir / "experiments" / "exp_01.yaml").write_text(
        "id: exp_01\ndescription: D\nmetrics: {acc: 90}\nhardware: H\ndataset: D\nseed: 42\nresults_file: r.json\n",
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: Claim 90% acc\nexperiment: exp_01\nsections: [results]\ncitations: [smith2024]\nstatus: verified\n",
        encoding="utf-8",
    )
    cit_path = pf_dir / "citations" / "smith2024.yaml"
    cit_path.write_text(
        "key: smith2024\ntitle: Real Title\ntype: article\nauthors: [Smith, A.]\nyear: 2024\n",
        encoding="utf-8",
    )

    run_build(tmp_path, no_reveal=True)
    bib1 = (tmp_path / "paper" / "references.bib").read_text(encoding="utf-8")
    assert "Real Title" in bib1

    cit_path.write_text(
        "key: smith2024\ntitle: Updated Title\ntype: article\nauthors: [Smith, A.]\nyear: 2024\n",
        encoding="utf-8",
    )

    run_build(tmp_path, no_reveal=True)
    bib2 = (tmp_path / "paper" / "references.bib").read_text(encoding="utf-8")
    assert "Updated Title" in bib2


def test_no_citation_yamls_falls_back_to_stubs(tmp_path: Path) -> None:
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "claims").mkdir(parents=True)
    (pf_dir / "experiments").mkdir(parents=True)

    (pf_dir / "paper.yaml").write_text(
        "title: Test\nauthors: [A]\nsections: [results]\nacknowledgment: Thanks\nbuild:\n  output_dir: 'paper'\n",
        encoding="utf-8",
    )
    (pf_dir / "experiments" / "exp_01.yaml").write_text(
        "id: exp_01\ndescription: D\nmetrics: {acc: 90}\nhardware: H\ndataset: D\nseed: 42\nresults_file: r.json\n",
        encoding="utf-8",
    )
    (pf_dir / "claims" / "claim_01.yaml").write_text(
        "id: claim_01\ntext: Claim 90% acc\nexperiment: exp_01\nsections: [results]\ncitations: [x2024]\nstatus: verified\n",
        encoding="utf-8",
    )

    run_build(tmp_path, no_reveal=True)
    bib_content = (tmp_path / "paper" / "references.bib").read_text(encoding="utf-8")
    assert "x2024" in bib_content
    assert "TODO" in bib_content
