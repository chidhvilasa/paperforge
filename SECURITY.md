# Security Policy

## Reporting a vulnerability

If you believe you have found a security vulnerability in PaperForge,
please report it privately rather than opening a public GitHub issue:

- Open a [GitHub Security Advisory](https://github.com/chidhvilasa/paperforge/security/advisories/new)
  for this repository, or
- If that is not available, open an issue at
  <https://github.com/chidhvilasa/paperforge/issues> with minimal detail
  and ask for a private channel to share the full report.

Please include:

- affected version;
- a minimal reproduction (fixture, not real research data);
- expected vs. actual behavior;
- potential impact.

There is no guaranteed response-time SLA at this time; this is a small,
independently maintained project. Reports are still taken seriously and
will be triaged as soon as possible.

## Scope

PaperForge runs `pdflatex`/`latexmk`/`bibtex` as subprocesses against
LaTeX generated from user-supplied project data, parses YAML project
files, reads/writes files under the project directory, and optionally
calls an external `llm` command for advisory AI review. Security reports
relevant to PaperForge specifically include (non-exhaustive):

- unsafe YAML loading (arbitrary code execution via `yaml.load`);
- path traversal or ZIP-slip in figure/asset resolution, packaging, or
  Overleaf ZIP extraction;
- shell/argument injection in subprocess invocations (`pdflatex`,
  `latexmk`, `bibtex`, `git`, `llm`);
- unrestricted formula/expression evaluation in derived-evidence
  handling;
- secrets or personal data leaking into generated LaTeX, packaged
  output, or logs.

See [`docs/SECURITY_MODEL.md`](docs/SECURITY_MODEL.md) if present for a
fuller threat model; if that document does not yet exist in the version
you are using, treat this file as the current source of truth.

## Supported versions

Only the latest released version on PyPI is actively supported.
