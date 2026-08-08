# Security model

This document describes what PaperForge actually defends against today and
where the boundary of that defense is. It does not claim completeness —
see [SECURITY_AUDIT.md](SECURITY_AUDIT.md) for the specific pass that
produced this document and its explicit "not reviewed" list.

## Threat model

PaperForge processes two categories of untrusted-ish input:

1. **Project content the user (or an agent acting for them) supplies**:
   `paperforge.project.yaml`, `.paperforge/paper.yaml`, claim/figure/table/
   citation YAML files, BibTeX, LaTeX templates, evidence file paths. This
   is "untrusted" in the sense that it may be malformed, oversized, or
   (if the project is ever shared/cloned from elsewhere) adversarial —
   but PaperForge does not treat the local user as an attacker; the goal
   is *safety against mistakes and malformed/malicious input*, not
   sandboxing a hostile local user from their own machine.
2. **Nothing external by default.** PaperForge makes no network calls
   during manifest loading, validation, migration, planning, or
   generation. `paperforge references --online` and `paperforge doctor`'s
   Crossref lookups are the only network-calling paths in the whole tool,
   and both are opt-in / explicitly flagged.

## What is defended, concretely

### YAML parsing (`paperforge.project_manifest.loader`)

- Only `yaml.SafeLoader`-derived construction is used — no
  `yaml.load()` without an explicit safe loader, no `unsafe_load`,
  no `FullLoader`, anywhere in the codebase (verified by repo-wide grep as
  part of this pass).
- Duplicate mapping keys are rejected (a custom loader override), not
  silently resolved to "last value wins".
- Document size (default 2 MB), nesting depth (default 40), collection
  size (default 10,000 items), and scalar string length (default 200,000
  chars) are all bounded, checked both before and after parsing.
- Self-referential (recursive) alias structures are rejected — both the
  case PyYAML's own eager mapping construction already refuses, and the
  case (self-referential sequences) that PyYAML's generator-based
  construction would otherwise silently allow, via a post-parse
  cycle-detecting structural walk.
- A cheap pre-parse scan rejects documents declaring an implausible number
  of YAML anchors before full parsing is even attempted.

### Path fields (`paperforge.project_manifest.path_safety`)

Every project-local path field routed through
`check_project_path`/`enforce_project_path` rejects: `..` traversal,
external absolute paths, Windows drive-letter absolute paths (`C:\...`),
UNC paths (`\\server\share\...`), and symlinks that resolve outside the
project root (checked via `os.path.realpath` comparison against each
existing ancestor component, without following the symlink for content
access).

### Subprocess execution (`paperforge.utils.subprocess_runner`)

- `shell=True` is never used anywhere in the codebase (verified by
  repo-wide grep).
- Every invocation through `run_subprocess` has a timeout with a safe
  default, and on timeout the *entire process tree* is killed
  (`taskkill /T` on Windows, `os.killpg(SIGKILL)` on POSIX) — not just the
  immediate child, so a `latexmk` that spawned `pdflatex`/`bibtex`
  children cannot leave them orphaned and running.
- Command strings are redacted (token/key/secret/password/auth-looking
  values masked) before appearing in any display string.

### Manifest structural/formula evaluation

There is no formula/derived-value evaluator anywhere in this codebase —
grep-verified (`eval(`, `exec(` do not appear anywhere in
`src/paperforge/`). `ClaimEntry`/provenance records have a `formula_refs`
field reserved for future use, but nothing currently evaluates a formula
string, so there is currently no formula-injection surface to defend.

### Archive handling

`paperforge export`'s Overleaf ZIP is only ever **created**
(`zipfile.ZipFile(path, "w", ...)`) from known, already-on-disk project
files — the codebase contains no ZIP **extraction** call anywhere
(grep-verified), so ZIP-slip (path traversal via a malicious archive
member name) is not a live risk in the current codebase because there is
no code path that extracts an untrusted archive at all.

### AI provider privacy (`paperforge.generation.providers`)

`ProviderConfig.validate()` refuses to construct any provider declaring
`privacy_class="external"` unless `redaction_enabled=True` is also set.
No external provider is implemented — the shipped `no_ai` and `fixture`
providers are both `privacy_class="local"` and make no network calls.

## What is explicitly *not* covered by this pass

- **LaTeX injection** into generated `.tex` output: existing
  `escape_latex`/`escape_latex_safe` helpers (shipped before this pass)
  were not re-audited here.
- **Template injection**: PaperForge does not use Jinja2 or any templating
  engine with expression evaluation (grep-verified — only Python f-strings
  and `str.format`), so classic SSTI is not applicable, but this was a
  spot-check, not an exhaustive audit of every f-string's inputs.
- **Dependency vulnerabilities**: see [SECURITY_AUDIT.md](SECURITY_AUDIT.md)
  for the one real finding from this pass (Pillow) and its fix.
- **Temp-file permissions**, **oversized-input DoS beyond the manifest
  loader**, **network timeout/redirect handling for `--online` reference
  verification**: not reviewed in this pass.

PaperForge does not claim any of the above are secure merely because no
exploit was demonstrated against them in this pass — "not reviewed" is
recorded honestly rather than silently, per [SECURITY_AUDIT.md](SECURITY_AUDIT.md).
