# Evidence and Provenance

PaperForge treats every scientific statement in a claim as belonging to
one of a fixed set of evidence classes. This exists to prevent a common
failure mode of automated or semi-automated paper drafting: a hypothesis,
interpretation, or placeholder silently turning into an asserted fact by
the time it reaches a submission PDF.

## The evidence classes

Set via the optional `evidence_class:` field on a claim
(`.paperforge/claims/<id>.yaml`):

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
`experiments:`, or `citations:` — at least one real evidence source. A
`DIRECT_RESULT`, `DERIVED_RESULT`, or `STATISTICAL_RESULT` claim with
none of these is flagged `EVIDENCE_CLASS_UNSUPPORTED_RESULT`.

## Example

```yaml
id: claim_07
text: "The adaptive scheduler reduces mean latency by 31.3% relative to the baseline (p=0.0020)."
experiment: exp_density_100
evidence_class: STATISTICAL_RESULT
sections: [results]
status: verified
```

```yaml
id: claim_08
text: "This suggests the scheduler generalizes to higher densities."
evidence_class: INTERPRETATION
sections: [discussion]
```

## Submission-mode enforcement

`paperforge doctor` (and therefore `paperforge build --mode submission`)
runs three checks:

- **`EVIDENCE_CLASS_PLACEHOLDER`** (ERROR) — any claim marked
  `PLACEHOLDER`.
- **`EVIDENCE_CLASS_UNSUPPORTED_RESULT`** (ERROR) — any
  `DIRECT_RESULT`/`DERIVED_RESULT`/`STATISTICAL_RESULT` claim with no
  linked experiment or citation.
- **`EVIDENCE_CLASS_INVALID`** (WARNING) — an `evidence_class` value that
  isn't one of the ten recognized classes (likely a typo).

Both ERROR-level checks are included in `SUBMISSION_BLOCKING`, so a
project with unresolved placeholders or unsupported result claims cannot
reach a "submission-ready" build.

## Backward compatibility

`evidence_class` is optional. An existing project with no
`evidence_class` set on any claim behaves exactly as before — none of
these three checks fire for an unclassified claim. Classification is
something a project opts into claim-by-claim, not a requirement imposed
retroactively.

## What this does not do (yet)

This is claim-level classification, not full claim-to-sentence
provenance tracking (a sidecar mapping every sentence of generated prose
to its exact source range, derivation, and confidence). That richer
provenance architecture is a larger undertaking and is not implemented
in the current release — see the project's changelog for what is
actually shipped in each version.
