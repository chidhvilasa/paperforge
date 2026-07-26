"""LaTeX utility functions."""

from __future__ import annotations


def escape_latex(text: str) -> str:
    """
    Escape LaTeX special characters in user-provided text.
    Must be applied to ALL user strings before LaTeX embedding.
    Order matters: backslash must be first.
    """
    if not text:
        return text
    text = text.replace("\\", "\x00BACKSLASH\x00")
    text = text.replace("&", "\\&")
    text = text.replace("%", "\\%")
    text = text.replace("$", "\\$")
    text = text.replace("#", "\\#")
    text = text.replace("_", "\\_")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    text = text.replace("~", "\x00TILDE\x00")
    text = text.replace("^", "\x00CIRCUM\x00")

    text = text.replace("\x00BACKSLASH\x00", "\\textbackslash{}")
    text = text.replace("\x00TILDE\x00", "\\textasciitilde{}")
    text = text.replace("\x00CIRCUM\x00", "\\textasciicircum{}")
    return text
