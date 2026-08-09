"""A safe formula evaluator for :class:`~paperforge.evidence.models.DerivedEvidence`.

This never calls Python's ``eval``/``exec``, never imports anything, and
never touches the filesystem, environment, or network. The formula string
is parsed with :mod:`ast` and walked by hand; only a small allow-listed
subset of the expression grammar is interpreted, and every node type is
checked against that allow-list *before* any evaluation happens (so a
rejected formula never partially executes).

Allowed grammar
----------------
- numeric literals (``int``/``float``)
- variable names, resolved against the ``operands`` mapping passed to
  :func:`evaluate`
- ``+ - * /`` and unary ``+ -``
- ``**`` with a literal, bounded exponent (``|exponent| <= MAX_EXPONENT``)
- parentheses (implicit in the AST -- no special-casing needed)
- calls to a small whitelist of pure math functions: ``abs``, ``min``,
  ``max``, ``round``, ``sqrt``

Everything else -- attribute access, subscripting, comprehensions, lambda,
``import``, function/class definitions, string/bytes/set/dict literals,
comparisons, boolean operators, walrus, f-strings, calls to anything not
whitelisted -- is rejected during the validation pass with a
:class:`FormulaSecurityError` naming the offending construct.
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field

MAX_EXPONENT = 12
MAX_FORMULA_LENGTH = 2000

_ALLOWED_BINOPS: dict[type[ast.operator], object] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a**b,
}

_ALLOWED_UNARY: dict[type[ast.unaryop], object] = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}

_ALLOWED_FUNCTIONS: dict[str, object] = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "sqrt": math.sqrt,
}


class FormulaSecurityError(ValueError):
    """A formula contained a construct outside the safe allow-list."""


class FormulaEvaluationError(ValueError):
    """A formula was syntactically safe but failed to evaluate (e.g.
    division by zero, or referenced an operand that was not provided)."""


@dataclass
class FormulaResult:
    value: float
    operand_names_used: set[str] = field(default_factory=set)


def _validate(node: ast.AST, *, depth: int = 0) -> None:
    if depth > 60:
        raise FormulaSecurityError("Formula is too deeply nested.")

    if isinstance(node, ast.Expression):
        _validate(node.body, depth=depth + 1)
        return
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, int | float):
            raise FormulaSecurityError(
                f"Only numeric literals are allowed, got {type(node.value).__name__!r}."
            )
        return
    if isinstance(node, ast.Name):
        return
    if isinstance(node, ast.BinOp):
        if type(node.op) not in _ALLOWED_BINOPS:
            raise FormulaSecurityError(
                f"Operator {type(node.op).__name__} is not permitted."
            )
        if isinstance(node.op, ast.Pow):
            exponent = node.right
            if not (
                isinstance(exponent, ast.Constant)
                and isinstance(exponent.value, int | float)
                and not isinstance(exponent.value, bool)
            ):
                raise FormulaSecurityError(
                    "Exponents must be a literal number (no variable exponents)."
                )
            if abs(exponent.value) > MAX_EXPONENT:
                raise FormulaSecurityError(
                    f"Exponent magnitude exceeds the bound of {MAX_EXPONENT}."
                )
        _validate(node.left, depth=depth + 1)
        _validate(node.right, depth=depth + 1)
        return
    if isinstance(node, ast.UnaryOp):
        if type(node.op) not in _ALLOWED_UNARY:
            raise FormulaSecurityError(
                f"Unary operator {type(node.op).__name__} is not permitted."
            )
        _validate(node.operand, depth=depth + 1)
        return
    if isinstance(node, ast.Call):
        if (
            not isinstance(node.func, ast.Name)
            or node.func.id not in _ALLOWED_FUNCTIONS
        ):
            name = getattr(node.func, "id", type(node.func).__name__)
            raise FormulaSecurityError(f"Function '{name}' is not permitted.")
        if node.keywords:
            raise FormulaSecurityError("Keyword arguments are not permitted.")
        for arg in node.args:
            _validate(arg, depth=depth + 1)
        return

    # Everything else is explicitly rejected: Attribute, Subscript, Lambda,
    # comprehensions, Import, walrus, comparisons, bool ops, strings, f-strings,
    # dict/set/list literals, Starred, function/class defs, etc.
    raise FormulaSecurityError(
        f"'{type(node).__name__}' is not permitted in a formula."
    )


def parse_and_validate(formula: str) -> ast.Expression:
    """Parse ``formula`` and reject anything outside the safe grammar.

    Raises :class:`FormulaSecurityError` (never a bare ``SyntaxError`` or
    Python exception from a rejected construct) for anything unsafe.
    """

    if not formula or not formula.strip():
        raise FormulaSecurityError("Formula must not be empty.")
    if len(formula) > MAX_FORMULA_LENGTH:
        raise FormulaSecurityError(
            f"Formula exceeds the maximum length of {MAX_FORMULA_LENGTH} characters."
        )
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as exc:
        raise FormulaSecurityError(f"Formula is not valid syntax: {exc}") from exc
    _validate(tree)
    return tree


def referenced_names(formula: str) -> set[str]:
    """Return the set of operand names a (validated) formula references."""

    tree = parse_and_validate(formula)
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}


def _eval_node(node: ast.AST, operands: dict[str, float], used: set[str]) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, operands, used)
    if isinstance(node, ast.Constant):
        # _validate already guarantees node.value is a non-bool int/float.
        value = node.value
        assert isinstance(value, int | float) and not isinstance(value, bool)
        return float(value)
    if isinstance(node, ast.Name):
        if node.id not in operands:
            raise FormulaEvaluationError(
                f"Formula references operand '{node.id}', which was not supplied."
            )
        used.add(node.id)
        return float(operands[node.id])
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, operands, used)
        right = _eval_node(node.right, operands, used)
        op_fn = _ALLOWED_BINOPS[type(node.op)]
        if isinstance(node.op, ast.Div) and right == 0:
            raise FormulaEvaluationError("Division by zero in formula.")
        return op_fn(left, right)  # type: ignore[operator]
    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, operands, used)
        return _ALLOWED_UNARY[type(node.op)](operand)  # type: ignore[operator]
    if isinstance(node, ast.Call):
        assert isinstance(node.func, ast.Name)
        fn = _ALLOWED_FUNCTIONS[node.func.id]
        args = [_eval_node(a, operands, used) for a in node.args]
        try:
            return float(fn(*args))  # type: ignore[operator]
        except ValueError as exc:
            raise FormulaEvaluationError(str(exc)) from exc
    # _validate already rejects anything else before we get here.
    raise FormulaSecurityError(
        f"'{type(node).__name__}' is not permitted in a formula."
    )


def evaluate(formula: str, operands: dict[str, float]) -> FormulaResult:
    """Safely evaluate ``formula`` against ``operands``.

    Validates the formula's grammar first (raising
    :class:`FormulaSecurityError` for anything unsafe), then evaluates it
    by walking the AST directly -- no ``eval``/``exec`` is ever invoked.
    """

    tree = parse_and_validate(formula)
    used: set[str] = set()
    value = _eval_node(tree, operands, used)
    return FormulaResult(value=value, operand_names_used=used)


__all__ = [
    "MAX_EXPONENT",
    "FormulaEvaluationError",
    "FormulaResult",
    "FormulaSecurityError",
    "evaluate",
    "parse_and_validate",
    "referenced_names",
]
