# Deterministic, evidence-safe generation

`paperforge generate` turns an approved [plan](GENERATION_PLANNING.md)
into section content, using only the `no_ai` provider by default (see
[AI_PROVIDERS.md](AI_PROVIDERS.md)).

## Command

```bash
paperforge generate [--section NAME | --regenerate NAME]
                     [--outline-only | --draft-with-placeholders]
                     [--provider no_ai|fixture] [--review-existing]
                     [--non-interactive] [--json]
```

With no `--section`/`--regenerate`, every section in the plan is
generated (this is the "generate `--all`" default).

## Modes

| Mode | Flag | Requires approval? | Output |
|---|---|---|---|
| Outline | `--outline-only` | No | `.paperforge/generated_sections/<section>.outline.json` — headings, purpose, permitted claim/evidence/citation/figure/table lists. Zero prose. |
| Draft with placeholders | `--draft-with-placeholders` | No | `.paperforge/generated_sections/<section>.md`, watermarked (`<!-- DRAFT WITH PLACEHOLDERS -- NOT SUBMISSION READY -->`), placeholder claims included and marked `**[PLACEHOLDER]**` inline |
| Validated (default) | *(none)* | **Yes** | `.paperforge/generated_sections/<section>.md`, no watermark, placeholder claims excluded entirely |

The validated (default) mode refuses to run without a currently-valid
`paperforge plan --approve`, returning exit code 40
(`EXIT_GENERATION_PROVENANCE_ERROR`) and the exact reason (missing
approval, or the specific stale-approval reasons from
`check_approval_validity`).

## What generated text actually is

Every generated sentence wraps one claim's **author-written**
`claim.text` in a short, neutral, evidence-class-specific template, e.g.:

> A direct result (c1) indicates: *the proposed method reduces p99 latency
> by 18% relative to baseline* (evidence: `results/latency.csv`).

> As asserted by the authors: *the system targets resource-constrained IoT
> deployments* [c4].

> \[PLACEHOLDER c9: *TBD* -- TODO: replace with real evidence before
> submission.\]

Nothing beyond the claim's own text, id, evidence references, and
citation keys ever appears in the sentence — no invented numbers, facts,
or citations. See `src/paperforge/generation/providers.py` for the full
template table.

## Provenance

Every generated sentence is paired with a provenance record — see
[EVIDENCE_AND_PROVENANCE.md](EVIDENCE_AND_PROVENANCE.md#provenance-sidecars).

## `--review-existing`

Lists already-generated sections (`.paperforge/generated_sections/*.md`)
without generating anything, for an agent or human to check what's already
been produced before deciding whether to `--regenerate` a section.

## Known limitation

Generated Markdown is **not yet wired into the LaTeX `build` pipeline** —
it is a standalone artifact under `.paperforge/generated_sections/`,
useful for review and for its provenance trail, but `paperforge build`
does not currently consume it. Integrating the two is future work.
