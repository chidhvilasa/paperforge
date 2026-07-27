
from pathlib import Path

from paperforge.commands.build import _generate_author_block_journal
from paperforge.commands.doctor import collect_issues
from paperforge.core.project import Affiliation, PaperForgeProject, ProjectConfig


def test_project_config_parses_affiliations():
    data = {
        "version": "0.1",
        "title": "T",
        "authors": ["A. Author"],
        "affiliations": [
            {
                "institution": "MIT",
                "department": "CS",
                "city": "Cambridge",
                "country": "USA"
            }
        ]
    }
    config = ProjectConfig.from_yaml(data)
    assert len(config.affiliations) == 1
    assert config.affiliations[0].institution == "MIT"
    assert config.affiliations[0].department == "CS"
    assert config.affiliations[0].city == "Cambridge"

def test_project_config_defaults_empty_affiliations():
    data = {
        "version": "0.1",
        "title": "T",
        "authors": ["A. Author"],
    }
    config = ProjectConfig.from_yaml(data)
    assert config.affiliations == []

def test_doctor_warns_missing_affiliation():
    config = ProjectConfig(version="0.1", title="T", authors=["A. Author"], venue="acm", status="draft", sections=[], build_output_dir=".", latex_template="ieee")
    project = PaperForgeProject(root=Path("."), config=config, claims=[], experiments=[], figures=[])
    issues = collect_issues(project)
    missing = [i for i in issues if i.code == "MISSING_AFFILIATION"]
    assert len(missing) == 1
    assert missing[0].severity == "WARNING"

def test_doctor_passes_when_affiliations_present():
    config = ProjectConfig(version="0.1", title="T", authors=["A. Author"], affiliations=[Affiliation(institution="MIT")], venue="acm", status="draft", sections=[], build_output_dir=".", latex_template="ieee")
    project = PaperForgeProject(root=Path("."), config=config, claims=[], experiments=[], figures=[])
    issues = collect_issues(project)
    missing = [i for i in issues if i.code == "MISSING_AFFILIATION"]
    assert len(missing) == 0

def test_journal_author_block_with_affiliations():
    authors = ["Alice", "Bob"]
    affiliations = [
        Affiliation(institution="Inst A", membership="Member"),
        Affiliation(institution="Inst B", country="US")
    ]
    block = _generate_author_block_journal(authors, affiliations)
    assert "Alice,~\\IEEEmembership{Member,~IEEE}" in block
    assert "\\thanks{Inst A}" in block
    assert "\\thanks{Inst B, US}" in block
    assert "IEEEcompsocitemizethanks" not in block

def test_journal_author_block_with_affiliations_compsoc():
    authors = ["Alice", "Bob"]
    affiliations = [
        Affiliation(institution="Inst A", membership="Member"),
        Affiliation(institution="Inst B", country="US")
    ]
    block = _generate_author_block_journal(authors, affiliations, compsoc=True)
    assert "Alice,~\\IEEEmembership{Member,~IEEE}" in block
    assert "Alice is with Inst A" in block
    assert "Bob is with Inst B, US" in block

def test_journal_author_block_no_affiliations_fallback():
    authors = ["Alice", "Bob"]
    block = _generate_author_block_journal(authors, [])
    assert block == "Alice, Bob"
