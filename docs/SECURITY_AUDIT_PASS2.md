# Security Audit — Completion Pass 2 (1.8.0)

Scope: the new evidence architecture, author-review workflow, and venue
versioning added in this pass. This audit does **not** cover the
interactive intake wizard, safe-import workflow, or the true isolated
staging-build lifecycle described in the original 30-phase specification
— none of those shipped in this pass (see
`audit_output/product_completion_pass2/` for why). Re-run this audit
against those subsystems once they exist.

## Evidence: formula injection

`paperforge.evidence.formula` parses every formula with `ast.parse` and
walks the tree against an explicit allow-list *before* any evaluation.
Verified rejected, with no side effect (no file created, no `os.system`
executed, no stdout from the attempted command):

- `__import__('os').system(...)`, `os.system(...)`, `exec(...)`, `eval(...)`
- `open('secret.txt').read()`
- attribute access (`a.__class__`, `a.__class__.__bases__`,
  `getattr(a, 'x')`)
- subscripting (`a[0]`)
- comprehensions (list/dict), lambda, f-strings, byte/string literals
- `import os`, multi-statement (`a; b`), conditional expressions,
  comparisons, boolean operators, `globals()`/`locals()`/`vars()`,
  starred expressions
- unbounded/variable exponents (`a ** b`, `a ** 999`) — bounded to
  `|exponent| <= 12` and literal-only

See `tests/test_evidence_formula.py` (24 parametrized unsafe-formula
cases plus explicit CLI-level injection tests in
`tests/test_evidence_cli.py::test_derived_add_rejects_injection_formula`).
The evaluator never calls Python's `eval`/`exec` under any code path —
verified by code inspection of `paperforge/evidence/formula.py` (the only
`eval`-shaped operation is the hand-written recursive `_eval_node`
interpreter, which only recognizes the same allow-listed node types the
validator already checked).

## Evidence: cyclic and huge graphs

- **Cycle via the CLI**: `derived add` requires every operand id to
  already exist in the store, which makes constructing a cycle through
  the CLI itself impossible (you cannot reference an id that doesn't yet
  exist).
- **Cycle via tampered state**: the on-disk YAML store is user-editable.
  `detect_cycles`/`topological_order`/`compute_staleness` are exercised
  against a hand-crafted cyclic `derived.yaml` (self-cycle, 2-node cycle,
  3-node cycle) in `tests/test_evidence_graph.py` and
  `tests/test_evidence_cli.py::test_evidence_graph_reports_cycle_from_tampered_state`
  — all detected, none crash, none hang.
- **Huge graph**: `MAX_GRAPH_NODES = 20_000`. A store exceeding that is
  rejected with `GraphError` before any traversal
  (`tests/test_evidence_graph.py::test_huge_graph_is_rejected`), a
  deliberate resource-exhaustion guard for `evidence graph --json`
  against a maliciously or accidentally huge evidence store.

## Evidence: source extraction

CSV/JSON/YAML extraction uses only stdlib `csv`/`json` and
`yaml.safe_load` — never `yaml.load`, never `pickle`, never a project's
own code. Source files are capped at 50MB
(`sources._read_bytes(max_size=...)`); direct-evidence source paths are
resolved through the same `project_manifest.path_safety.check_project_path`
traversal guard used for manifest fields (`..`, external absolute,
drive-letter, UNC, symlink-escape all rejected).

## Venues: path traversal and YAML safety

`load_custom_venue` resolves its path through `check_project_path` before
opening anything. Verified rejected:
`../../../../../../etc/passwd`, `../outside.yaml`, and (CLI-level)
`../../outside.yaml` via `paperforge venue show --custom-file` — see
`tests/test_venue_versioning.py::test_custom_venue_path_traversal_rejected`
and `::test_custom_venue_cli_rejects_traversal`. Parsing uses
`yaml.safe_load`; a `!!python/object/apply:os.system` tag is rejected
(`test_venue_yaml_safety_no_arbitrary_python_tags`) — PyYAML's
`SafeLoader` has no constructor for that tag and raises rather than
constructing an arbitrary object.

## Review workflow: stale-object approval / hash mismatch

`paperforge.review.approvals.reconcile` re-hashes every previously
"approved" object on every `list`/`approve`/`reject`/`reset` call. An
object edited after approval (a mutated evidence value, in the test) is
detected via hash mismatch and downgraded back to `pending` automatically
— verified end-to-end (direct-YAML tamper, then `reconcile`) in
`tests/test_approvals.py::test_stale_approval_downgrades_to_pending` and
the CLI-level `tests/test_evidence_cli.py`/`test_approvals.py` suite. A
decision can never be recorded against an object id that doesn't resolve
to a known provenance sentence, claim, or evidence record
(`ApprovalError`, tested).

## Subprocess timeout (unchanged, re-verified)

No new subprocess execution paths were added in this pass. The existing
centralized, timeout-safe subprocess runner
(`paperforge.utils.subprocess_runner`, 300s ceiling, process-tree cleanup)
introduced in 1.7.0 is untouched; full regression (841 tests) still
passes, including its existing coverage.

## Not covered by this pass (see docs/VERSION_DECISION_1_8.md)

- Intake input-length limits, terminal escape characters, state
  corruption — no intake subsystem exists.
- Reference-network hardening (timeouts, redirects, response-size caps,
  malformed JSON) — no new reference-network code was added in this pass;
  1.7.0's existing `reference_verifier.py` behavior is unchanged and was
  not re-audited here.
- Staging-build symlink escape / interrupted rename / crash recovery — no
  new staging-build lifecycle was added in this pass; `outputs/lifecycle.py`
  (promote/rollback) is unchanged from 1.7.0.
