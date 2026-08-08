# Generation planning and approval

`paperforge plan` builds a **structural** plan from the manifest — section
order, purpose, in-scope claim/evidence/citation/figure/table references
per section, unresolved questions, prohibited claims, venue constraints,
expected outputs, and validation gates. It never contains manuscript
prose.

## Command

```bash
paperforge plan [--section NAME] [--approve] [--revoke-approval]
                 [--mode submission] [--non-interactive] [--json]
```

Every invocation rebuilds the plan fresh from the current manifest and
writes:

- `.paperforge/generation_plan.md`
- `.paperforge/generation_plan.json`

`--approve` additionally writes `.paperforge/plan_approval.json` and
refuses if the manifest fails baseline structural validation.

## How claims are routed to sections

Each non-`PLACEHOLDER` claim is assigned to a section using a small,
documented heuristic based on its `evidence_class` (e.g. `DIRECT_RESULT` →
`results`, `LIMITATION` → `discussion`, `FUTURE_WORK` → `conclusion`),
falling back to the first section if no match. `PLACEHOLDER` claims are
never assigned to a section — they're collected into `prohibited_claims`
instead, since generation must never turn a placeholder into prose.

## Approval

Approval (`--approve`) records four independent SHA-256 hashes:

- `manifest_hash` — the full manifest content
- `evidence_hash` — the evidence inventory + bibliography list
- `claim_set_hash` — every claim's id, text, evidence class, and evidence refs
- `plan_hash` — the plan's structure (sections, venue constraints, etc.), excluding its timestamp

plus the target `venue`, a `timestamp`, the `approver` (the local git
`user.name`, or `"agent"` when `--non-interactive` is passed), and `mode`.

**Automatic invalidation.** `paperforge plan` (with or without flags)
always recomputes these same four hashes against the *current* manifest
and plan and reports `approval_status`: `none`, `valid`, `stale`, or
`corrupt`, plus the specific reasons when stale. Any edit to the manifest,
its evidence, its claims, its venue, or the plan's own structure
invalidates a prior approval — there is no separate bespoke "did X change"
check per field; recomputing the hashes catches all of them uniformly.

## Why generation is gated

`paperforge generate`'s default mode refuses to run without a currently
valid approval (see [GENERATION.md](GENERATION.md)) — the plan/approval
step exists specifically so a human (or an agent acting under human
supervision) reviews *what will be generated* before any prose exists,
rather than reviewing prose after the fact.

`--outline-only` and `--draft-with-placeholders` generation modes never
require approval, since neither produces submission-track content.
