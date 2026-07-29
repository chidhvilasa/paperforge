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

    # Step 1: Backslash
    text = text.replace("\\", "\x00BACKSLASH\x00")

    # Step 2: Special LaTeX characters
    text = text.replace("&", "\\&")
    text = text.replace("%", "\\%")
    text = text.replace("$", "\\$")
    text = text.replace("#", "\\#")
    text = text.replace("_", "\\_")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    text = text.replace("~", "\x00TILDE\x00")
    text = text.replace("^", "\x00CIRCUM\x00")

    # Step 3: Unicode typography
    text = text.replace("—", "---")  # U+2014 Em-dash
    text = text.replace("–", "--")   # U+2013 En-dash
    text = text.replace("\u2019", "'")  # Right single quote / apostrophe
    text = text.replace("\u2018", "`")  # Left single quote
    text = text.replace("\u201c", "``") # Left double quote
    text = text.replace("\u201d", "''") # Right double quote
    text = text.replace("…", "\\ldots{}")  # U+2026 Ellipsis
    text = text.replace("\u00a0", "~")  # Non-breaking space

    # Step 4: Unicode math & symbols
    text = text.replace("°", "$^\\circ$")
    text = text.replace("×", "$\\times$")

    # Common Greek letters
    text = text.replace("α", "$\\alpha$")
    text = text.replace("β", "$\\beta$")
    text = text.replace("γ", "$\\gamma$")
    text = text.replace("δ", "$\\delta$")
    text = text.replace("ε", "$\\epsilon$")
    text = text.replace("θ", "$\\theta$")
    text = text.replace("λ", "$\\lambda$")
    text = text.replace("μ", "$\\mu$")
    text = text.replace("π", "$\\pi$")
    text = text.replace("σ", "$\\sigma$")
    text = text.replace("τ", "$\\tau$")
    text = text.replace("φ", "$\\phi$")
    text = text.replace("ω", "$\\omega$")
    text = text.replace("Δ", "$\\Delta$")
    text = text.replace("Σ", "$\\Sigma$")
    text = text.replace("Ω", "$\\Omega$")

    # Finalize placeholder tokens for backslash, tilde, circumflex
    text = text.replace("\x00BACKSLASH\x00", "\\textbackslash{}")
    text = text.replace("\x00TILDE\x00", "\\textasciitilde{}")
    text = text.replace("\x00CIRCUM\x00", "\\textasciicircum{}")
    return text


def markdown_to_latex_inline(text: str) -> str:
    """Convert inline Markdown formatting to LaTeX commands.

    Applied AFTER escape_latex() so the conversion targets
    already-escaped text where needed. Called only when is_math=False.

    Handles:
      Markdown headers (## Heading) -> \\textbf{Heading}
      Markdown links [text](url) -> \\href{url}{text}
      Markdown bullet lists -> \\begin{itemize}\\item ...\\end{itemize}
      Markdown numbered lists -> \\begin{enumerate}\\item ...\\end{enumerate}
      Bare URLs -> \\url{url}
      **text** -> \\textbf{text}
      *text*   -> \\textit{text}
      `text`   -> \\texttt{text}
    """
    if not text:
        return text

    # Markdown headers in claim text (e.g. ## Heading -> \textbf{Heading})
    text = re.sub(r"^(?:#+)\s*(.+)$", r"\\textbf{\1}", text, flags=re.MULTILINE)

    # Markdown links: [text](url) -> \href{url}{text}
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\\href{\2}{\1}", text)

    # Markdown bullet lists: "- item" or "* item"
    bullet_items = re.findall(r"^\s*[*|-]\s+(.+)$", text, flags=re.MULTILINE)
    if bullet_items:
        items_str = "\n".join(f"  \\item {it}" for it in bullet_items)
        list_block = f"\\begin{{itemize}}\n{items_str}\n\\end{{itemize}}"
        text = re.sub(r"(?:^\s*[*|-]\s+.+$\n?)+", list_block + "\n", text, flags=re.MULTILINE)

    # Markdown numbered lists: "1. item"
    num_items = re.findall(r"^\s*\d+\.\s+(.+)$", text, flags=re.MULTILINE)
    if num_items and not bullet_items:
        items_str = "\n".join(f"  \\item {it}" for it in num_items)
        list_block = f"\\begin{{enumerate}}\n{items_str}\n\\end{{enumerate}}"
        text = re.sub(r"(?:^\s*\d+\.\s+.+$\n?)+", list_block + "\n", text, flags=re.MULTILINE)

    # Bare URLs: http://... or https://... -> \url{...} (avoid replacing already converted \href)
    text = re.sub(r"(?<!\\href\{)(?<!\\url\{)(https?://[^\s{}()]+)", r"\\url{\1}", text)

    # Bold (** must come before * to avoid partial match)
    text = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"\\textit{\1}", text)
    # Code/monospace
    text = re.sub(r"`(.+?)`", r"\\texttt{\1}", text)
    return text


REQUIRED_PLACEHOLDER_PATTERN = r"\[REQUIRED[^\]]*\]"


def emit_required_placeholder(field_name: str) -> str:
    """Emit a structured placeholder for missing required info.
    These are caught by the artifact check and block build.
    """
    return f"[REQUIRED INFORMATION MISSING: {field_name}]"


convert_markdown_to_latex = markdown_to_latex_inline
