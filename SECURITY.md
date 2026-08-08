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
- path traversal in figure/asset resolution, manifest path fields, or
  packaging (the Overleaf ZIP is only ever *created*, never extracted, by
  any code in this repository — ZIP-slip would require a future feature
  that extracts an untrusted archive, which does not currently exist);
- shell/argument injection in subprocess invocations (`pdflatex`,
  `latexmk`, `bibtex`, `git`, `llm`);
- unrestricted formula/expression evaluation (no formula evaluator
  currently exists in this codebase; `eval`/`exec` do not appear anywhere
  in `src/paperforge/`, verified by repo-wide search);
- secrets or personal data leaking into generated LaTeX, packaged
  output, or logs.

See [`docs/SECURITY_MODEL.md`](docs/SECURITY_MODEL.md) for the fuller
threat model, [`docs/SECURITY_AUDIT.md`](docs/SECURITY_AUDIT.md) for the
audit log behind it, and [`docs/PRIVACY.md`](docs/PRIVACY.md) for what
does and does not leave your machine.

## Supported versions

Only the latest released version on PyPI is actively supported.
