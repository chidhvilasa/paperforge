from paperforge.commands.validate import _extract_all_numbers, _numbers_match_loose
from paperforge.models.citation import Citation


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
