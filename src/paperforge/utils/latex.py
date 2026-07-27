"""LaTeX utility functions."""

from __future__ import annotations

import re


def escape_latex_safe(text: str, raw: bool = False) -> str:
    """Escape LaTeX special characters.

    If raw=True: return text unchanged (caller asserts it is already valid LaTeX).
    """
    if raw or not text:
        return text
    return escape_latex(text)


def escape_latex(text: str) -> str:
    """Escape LaTeX special characters in user text.

    Protects inline math spans ($...$, $$...$$, \\(...\\)) from escaping.
    For full LaTeX content, set is_math: true on the claim.
    """
    if not text:
        return text

    # Split pattern: $$...$$ and $...$ (non-greedy) and \(...\)
    parts = re.split(r"(\$\$.*?\$\$|\$[^$]*?\$|\\\(.*?\\\))", text, flags=re.DOTALL)

    result = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            # Math span — pass through unchanged
            result.append(part)
        else:
            # Plain text — escape special characters
            result.append(_escape_text(part))

    return "".join(result)


def _escape_text(text: str) -> str:
    """Apply LaTeX escaping to plain text (no math)."""
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


def markdown_to_latex_inline(text: str) -> str:
    """Convert inline Markdown formatting to LaTeX commands.

    Applied AFTER escape_latex() so the conversion targets
    already-escaped text where needed. Called only when is_math=False.

    Handles:
      **text** -> \\textbf{text}
      *text*   -> \\textit{text}
      `text`   -> \\texttt{text}
    """
    if not text:
        return text

    # Bold (** must come before * to avoid partial match)
    text = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"\\textit{\1}", text)
    # Code/monospace
    text = re.sub(r"`(.+?)`", r"\\texttt{\1}", text)
    return text


convert_markdown_to_latex = markdown_to_latex_inline
