"""Tests for the safe AST formula evaluator (paperforge.evidence.formula)."""

from __future__ import annotations

import pytest

from paperforge.evidence.formula import (
    FormulaEvaluationError,
    FormulaSecurityError,
    evaluate,
    referenced_names,
)


def test_addition() -> None:
    assert evaluate("a + b", {"a": 2, "b": 3}).value == 5


def test_subtraction() -> None:
    assert evaluate("a - b", {"a": 10, "b": 4}).value == 6


def test_percentage_reduction_formula() -> None:
    result = evaluate(
        "(baseline - adaptive) / baseline * 100", {"baseline": 120.5, "adaptive": 80.2}
    )
    assert result.value == pytest.approx(33.44, abs=0.01)
    assert result.operand_names_used == {"baseline", "adaptive"}


def test_division() -> None:
    assert evaluate("a / b", {"a": 100, "b": 4}).value == 25


def test_division_by_zero_raises() -> None:
    with pytest.raises(FormulaEvaluationError):
        evaluate("a / b", {"a": 1, "b": 0})


def test_unary_and_parentheses() -> None:
    assert evaluate("-(a + b)", {"a": 1, "b": 2}).value == -3


def test_bounded_exponent_ok() -> None:
    assert evaluate("a ** 2", {"a": 3}).value == 9


def test_exponent_over_bound_rejected() -> None:
    with pytest.raises(FormulaSecurityError):
        evaluate("a ** 999", {"a": 2})


def test_variable_exponent_rejected() -> None:
    with pytest.raises(FormulaSecurityError):
        evaluate("a ** b", {"a": 2, "b": 3})


def test_whitelisted_functions() -> None:
    assert evaluate("abs(a)", {"a": -5}).value == 5
    assert evaluate("min(a, b)", {"a": 3, "b": 7}).value == 3
    assert evaluate("max(a, b)", {"a": 3, "b": 7}).value == 7
    assert evaluate("round(a)", {"a": 2.6}).value == 3
    assert evaluate("sqrt(a)", {"a": 9}).value == 3


@pytest.mark.parametrize(
    "formula",
    [
        "__import__('os').system('echo pwned')",
        "os.system('echo pwned')",
        "open('secret.txt').read()",
        "a.__class__",
        "a.__class__.__bases__",
        "[x for x in range(10)]",
        "{x: x for x in range(10)}",
        "(lambda x: x)(1)",
        "exec('a=1')",
        "eval('1+1')",
        "import os",
        "a; b",
        "a if b else 0",
        "a == b",
        "a and b",
        "'string literal'",
        "b'bytes literal'",
        "a[0]",
        "f'{a}'",
        "globals()",
        "locals()",
        "vars()",
        "getattr(a, 'x')",
        "*a,",
    ],
)
def test_unsafe_formulas_are_rejected(formula: str) -> None:
    with pytest.raises(FormulaSecurityError):
        evaluate(formula, {"a": 1, "b": 2})


def test_missing_operand_raises() -> None:
    with pytest.raises(FormulaEvaluationError):
        evaluate("a + b", {"a": 1})


def test_referenced_names() -> None:
    assert referenced_names("(a + b) * c") == {"a", "b", "c"}


def test_empty_formula_rejected() -> None:
    with pytest.raises(FormulaSecurityError):
        evaluate("", {})


def test_overlong_formula_rejected() -> None:
    with pytest.raises(FormulaSecurityError):
        evaluate("a" + " + a" * 2000, {"a": 1})


def test_deeply_nested_formula_rejected() -> None:
    # Parentheses alone don't create AST depth (they collapse to the inner
    # node), so exercise the depth bound with genuinely nested binary
    # operators instead.
    formula = "a" + " + a" * 200
    with pytest.raises((FormulaSecurityError, RecursionError, SyntaxError)):
        evaluate(formula, {"a": 1})
