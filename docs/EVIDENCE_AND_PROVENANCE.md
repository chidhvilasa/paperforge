# Evidence and Provenance

PaperForge treats every scientific statement in a claim as belonging to
one of a fixed set of evidence classes. This exists to prevent a common
failure mode of automated or semi-automated paper drafting: a hypothesis,
interpretation, or placeholder silently turning into an asserted fact by
the time it reaches a submission PDF.

## The evidence classes

Set via the optional `evidence_class:` field on a claim
(`.paperforge/claims/<id>.yaml`, or `claims[].evidence_class` in the
canonical manifest):

| Class | Meaning | Requires linked evidence? |
|---|---|---|
| `AUTHOR_ASSERTED` | A statement the author is making directly | No |
| `SOURCE_SUPPORTED` | Supported by a cited external source | No (but should carry a `citations:` entry) |
| `DIRECT_RESULT` | A directly measured/observed result | **Yes** |
| `DERIVED_RESULT` | Computed from other evidence via a formula | **Yes** |
| `STATISTICAL_RESULT` | The output of a statistical test | **Yes** |
| `INTERPRETATION` | The author's reading of a result, not the result itself | No |
| `HYPOTHESIS` | A proposed explanation not yet established | No |
| `LIMITATION` | A stated constraint or weakness of the work | No |
| `FUTURE_WORK` | Planned or suggested next steps | No |
| `PLACEHOLDER` | Known-incomplete text, explicitly flagged | Always blocks submission until resolved |

"Requires linked evidence" means the claim must set `experiment:`,
`experiments:`, or `citations:` (legacy claim workflow) or
`evidence_refs:` / `citation_keys:` (manifest workflow) — at least one
real evidence source. A `DIRECT_RESULT`, `DERIVED_RESULT`, or
`STATISTICAL_RESULT` claim with none of these is flagged
`EVIDENCE_CLASS_UNSUPPORTED_RESULT` (legacy) or
`PROVENANCE_MISSING_EVIDENCE` (manifest workflow).

## The evidence architecture (`paperforge evidence ...`, since 1.8.0)

`DIRECT_RESULT`/`DERIVED_RESULT`/`STATISTICAL_RESULT` claims can now point
at a real, typed, hash-tracked evidence record instead of just a free-text
`evidence_refs:` string. Evidence records live in
`.paperforge/evidence/{direct,derived,statistical}.yaml` and are managed
with `paperforge evidence ...`. None of this is required — `evidence_refs`
can still be an arbitrary string for a claim whose evidence lives
elsewhere — but when a result claim's evidence *is* registered this way,
PaperForge can detect when it goes stale.

### DirectEvidence

A value read verbatim from a source file, or supplied manually by an
author. Never parses arbitrary project code — only CSV (cell lookup),
JSON (dotted path), and YAML (dotted path), via the stdlib `csv`/`json`
modules and `yaml.safe_load`.

```bash
paperforge evidence direct add --id baseline_latency \
  --type csv --source-path results/latency.csv \
  --source-locator "row=0;col=latency_ms" --unit ms
```

`content_hash` is the SHA-256 of the *entire source file*, computed at
record time. `paperforge evidence validate` (or `evidence direct
validate`) recomputes it and reports `EVIDENCE_STALE_DIRECT` if the file
changed since the value was recorded — deliberately coarse (the whole
file, not just the cell read) so an edit anywhere in the source is never
silently missed.

### DerivedEvidence

A value computed from other evidence via a formula evaluated by the
**safe AST evaluator** in `paperforge.evidence.formula` — never Python's
`eval`/`exec`. The formula string is parsed with `ast.parse` and walked
node-by-node against an allow-list (numeric literals, `+ - * /`, a
bounded-exponent `**`, parentheses, and the functions `abs`/`min`/`max`/
`round`/`sqrt`); anything else — attribute access, subscripting,
comprehensions, imports, calls to anything else, string/f-string
literals, comparisons — is rejected before any evaluation happens.

```bash
paperforge evidence derived add --id latency_reduction \
  --formula "(baseline_latency - adaptive_latency) / baseline_latency * 100" \
  --operands baseline_latency,adaptive_latency --unit percent --precision 2
```

Operand ids must already exist in the store (this makes a *retroactive*
cycle impossible through the CLI); a `dependency_hash` covering the
formula and every operand's current effective hash is stored alongside
the result. `paperforge evidence graph` / `paperforge evidence validate`
detect cycles (via DFS over the operand graph — relevant if the on-disk
YAML is edited by hand) and report `EVIDENCE_STALE_DERIVED` when an
upstream value or the formula itself has changed since the result was
last computed.

Units are a small bounded registry (`paperforge.evidence.units`), not a
symbolic algebra engine: `seconds`/`milliseconds`/`microseconds` and
`bytes`/`kilobytes`/`megabytes` convert exactly; `+`/`-` between operands
with incompatible unit categories (e.g. `milliseconds + percent`) is
rejected as `EVIDENCE_INCOMPATIBLE_UNITS`.

### StatisticalEvidence

An explicitly recorded statistical result — test name, statistic,
p-value, adjusted p-value, correction family/method, effect size,
confidence interval, alpha, assumptions, software/version. **PaperForge
never runs a statistical test automatically or chooses one from prose.**
You record the result you already computed:

```bash
paperforge evidence statistical add --id latency_reduction_sig \
  --test-name paired_t_test --statistic -4.12 --p-value 0.0018 \
  --sample-size 30 --paired --alpha 0.05 \
  --effect-size-name cohens_d --effect-size-value 0.82 \
  --confidence-interval "-18.2,-9.4" \
  --observation-refs baseline_latency,adaptive_latency
```

Validated: `p_value`/`adjusted_p_value` in `[0, 1]`, positive sample size,
paired tests have exactly two groups, confidence-interval bounds are
ordered, alpha in `(0, 1)`, and a handful of well-known effect sizes
(`pearson_r`, `spearman_rho`, `eta_squared`, `partial_eta_squared`,
`r_squared`) are range-checked. Two multiple-comparison correction
families are implemented as pure functions:
`paperforge.evidence.models.bonferroni_correction` and
`.holm_correction` (Holm-Bonferroni step-down). **A non-significant
result is never treated as evidence of equivalence** — PaperForge does
not infer or assert that from a large p-value; that inference, if made,
is the author's, recorded as an `INTERPRETATION` claim.

### The dependency graph

`paperforge evidence graph [--json]` shows every node (direct/derived/
statistical) and edge (`operand_of`, `observation_of`), any cycles, any
missing references, and the current stale set. `paperforge evidence
validate [--json]` runs full validation: per-record checks, cycles,
missing references, and staleness — exit code `45`
(`EXIT_EVIDENCE_ERROR`) on any error.

Staleness propagates:

- an edited direct-evidence source file → that `DirectEvidence` is stale;
- → every `DerivedEvidence` that (transitively) depends on it is stale;
- → every `StatisticalEvidence` whose `observation_refs` include it is
  stale;
- → `paperforge plan`'s approval hash includes a fingerprint of the whole
  evidence store, so **registering or changing evidence invalidates an
  existing plan approval** (`paperforge plan` reports
  `approval_status: stale`, listing the reason);
- → `paperforge provenance validate` reports `PROVENANCE_STALE_EVIDENCE`
  for any generated sentence whose `evidence_refs` point at now-stale
  evidence.

A graph larger than 20,000 total nodes is refused outright
(`EXIT_EVIDENCE_ERROR`) rather than traversed, as a resource-exhaustion
guard.

## Author review (`paperforge approvals ...`, since 1.8.0)

Reviewable objects — a generated provenance sentence, a manifest claim, or
a direct/derived/statistical evidence record — carry an
`author_review_status` (`pending`/`approved`/`rejected`). This is a
separate command group from the pre-existing `paperforge review` (an
AI-assisted *advisory* review that shells out to the `llm` CLI tool and
is unrelated to this workflow):

```bash
paperforge approvals approve latency_reduction --reviewer alice
paperforge approvals approve --section results   # every generated sentence in a section
paperforge approvals list --json
```

Every decision is appended to `.paperforge/approvals.json` with the
reviewer, timestamp, decision, an optional note, and a content hash of
the object *at decision time*. `paperforge approvals list` (and every
`approve`/`reject`/`reset` call) first **reconciles**: it re-hashes every
previously-approved object, and if the hash no longer matches — the
sentence was regenerated, the claim was edited, the evidence value
changed — the approval is downgraded back to `pending` and reported as
stale (`stale: true`), rather than silently remaining "approved" against
content that no longer exists. Submission mode requires
`author_review_status` to be `approved`/`reviewed` for every generated
`DIRECT_RESULT`/`DERIVED_RESULT`/`STATISTICAL_RESULT` sentence.

## A complete example

```
raw_latency.csv (100 runs, baseline vs. adaptive scheduler)
    |
    +-- paperforge evidence direct add --id baseline_latency --type csv ...
    +-- paperforge evidence direct add --id adaptive_latency --type csv ...
    |
    v
paperforge evidence derived add --id latency_reduction \
    --formula "(baseline_latency - adaptive_latency) / baseline_latency * 100" \
    --operands baseline_latency,adaptive_latency
    |
    v
claim claim_latency_reduction:
    text: "The adaptive scheduler reduces mean latency by {{latency_reduction}}%."
    evidence_class: DERIVED_RESULT
    evidence_refs: [latency_reduction]
    |
    v
paperforge generate --provider no_ai
    -> generated sentence in results.md
    -> ProvenanceRecord{ sentence_id: "results:claim_latency_reduction",
                          text_hash, evidence_refs: [latency_reduction], ... }
    |
    v
paperforge approvals approve results:claim_latency_reduction --reviewer alice
```

Statistical variant, with raw paired observations recorded first as two
`DirectEvidence` series (one row per run) and the test result recorded
explicitly (never auto-run):

```
paperforge evidence direct add --id baseline_latency_run0 --type csv --source-locator "row=0;col=latency_ms" ...
paperforge evidence direct add --id adaptive_latency_run0 --type csv --source-locator "row=0;col=latency_ms" ...
... (one pair per run)

paperforge evidence statistical add --id latency_reduction_sig \
    --test-name paired_t_test --statistic -4.12 --p-value 0.0018 --sample-size 30 --paired \
    --observation-refs baseline_latency_run0,adaptive_latency_run0,...

claim claim_latency_significant:
    text: "This reduction is statistically significant (paired t-test, p=0.0018)."
    evidence_class: STATISTICAL_RESULT
    evidence_refs: [latency_reduction_sig]
```

If `raw_latency.csv` is later edited, `baseline_latency`/`adaptive_latency`
become `EVIDENCE_STALE_DIRECT`, `latency_reduction` becomes
`EVIDENCE_STALE_DERIVED`, both claims' provenance is flagged
`PROVENANCE_STALE_EVIDENCE`, and the plan approval is invalidated — the
whole chain, not just the file that changed.

## Submission-mode enforcement

`paperforge doctor` (and therefore `paperforge build --mode submission`)
runs three claim-level checks:

- **`EVIDENCE_CLASS_PLACEHOLDER`** (ERROR) — any claim marked
  `PLACEHOLDER`.
- **`EVIDENCE_CLASS_UNSUPPORTED_RESULT`** (ERROR) — any
  `DIRECT_RESULT`/`DERIVED_RESULT`/`STATISTICAL_RESULT` claim with no
  linked experiment or citation.
- **`EVIDENCE_CLASS_INVALID`** (WARNING) — an `evidence_class` value that
  isn't one of the ten recognized classes (likely a typo).

`paperforge provenance validate` additionally checks (manifest workflow):
per-sentence staleness (below), a missing generated file, a claim id no
longer in the manifest, a result-shaped claim with no evidence/citation
reference, a result-shaped claim not yet author-reviewed, stale-evidence
references, and placeholder provenance.

`paperforge evidence validate` checks the evidence store itself:
malformed records, unsafe formulas, missing/undeclared operands,
incompatible units, dependency cycles, and staleness.

## Provenance sidecars and per-sentence staleness

Since v1.7.0, the [canonical `paperforge.project.yaml` manifest
workflow](PROJECT_MANIFEST.md) adds real, sentence-level provenance: every
sentence `paperforge generate` produces gets one `ProvenanceRecord` —
section, sentence id, a SHA-256 hash of its exact text, evidence class,
claim IDs, evidence refs, citation keys, generation method, provider,
model, confidence, timestamp, author-review status, and warnings —
written to `.paperforge/provenance/<section>.json` plus a
`.paperforge/provenance/index.json` summary (a per-section index kept for
efficient validation without re-parsing every record).

**Since 1.8.0, staleness is checked at sentence granularity, not just
whole-section.** When a section's overall markdown hash no longer matches
what's recorded, `paperforge provenance validate` parses the current file
back into per-sentence text (matching how `generate` renders each
sentence on its own line) and compares each one's hash individually. Only
the sentence(s) that actually changed are reported
(`PROVENANCE_STALE_SENTENCE`); a hand-edit to one sentence does not
invalidate the recorded review of every other sentence in the same
section. If the sentence count itself changed (lines added/removed) or
the file no longer looks like PaperForge-generated markdown at all, the
check safely falls back to whole-section staleness
(`PROVENANCE_STALE_HASH`, ERROR) rather than guessing at a sentence split.

See [GENERATION.md](GENERATION.md) and
[docs/AGENT_INTEGRATION.md](AGENT_INTEGRATION.md) for a worked example of
the generation pipeline itself.

## Backward compatibility

- `evidence_class` remains optional; an unclassified claim behaves
  exactly as before.
- The evidence store (`paperforge evidence ...`) is entirely additive: a
  project that never runs any `evidence` command has an empty store, and
  every hash/staleness check involving it (plan approval, provenance
  validation) is then a no-op, matching pre-1.8.0 behavior exactly.
- Old `ProvenanceRecord` JSON sidecars (without the fields introduced
  since) still load; missing fields take their documented defaults.

## What this does not do (yet)

- The original `.paperforge/paper.yaml` claim-level `evidence_class`
  checks remain claim-level only — not connected to the manifest
  workflow's evidence store or sentence-level provenance, which only
  exist for content produced by `paperforge generate` from the canonical
  manifest workflow.
- No automatic statistical test execution (by design — see
  "StatisticalEvidence" above). Only `bonferroni`/`holm` correction and a
  handful of range-checked effect sizes are implemented; anything else is
  recorded but not range-validated.
- Full-text claim-support verification against a reference's actual paper
  text is not implemented — see [reference_verification.md](reference_verification.md)
  for the metadata-only vs. claim-support distinction that already exists
  and is not weakened by anything in this document.
- Generated content from `paperforge generate` is not wired into the
  LaTeX `build` pipeline.
