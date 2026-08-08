# Agent integration: a worked example

This walks through the full agent workflow against
[`examples/agent_project/`](../examples/agent_project/) — a small,
entirely fictional fixture. Every command and its actual result below was
verified against this exact fixture as part of this release (not
hypothetical output).

```bash
cd examples/agent_project

# 1. Structural sanity check
paperforge manifest validate paperforge.project.yaml --mode draft --json
# -> status: success, exit_code: 0

# 2. What's missing for submission?
paperforge requirements --mode submission --json
# -> status: failure, exit_code: 21
#    outputs.blocking: 1
#    errors: [{"code": "REQ-BIBLIOGRAPHY-FILE-references.bib", ...}]
#    (the fixture intentionally omits references.bib to demonstrate a
#    real, specific, actionable failure -- not a false "all clear")

# 3. Build and approve a plan
paperforge plan --json
# -> status: success; outputs.plan.sections lists introduction, methodology,
#    results, discussion, etc. with claim/evidence/citation refs per section

paperforge plan --approve --mode submission --non-interactive --json
# -> status: success; outputs.approved: true; approver recorded as "agent"

# 4. Generate
paperforge generate --outline-only --json         # -> status: success, no prose
paperforge generate --json                        # -> status: success (approval from step 3 is valid)

# 5. Validate provenance
paperforge provenance validate --json
# -> status: failure, exit_code: 40
#    errors: [PROVENANCE_UNREVIEWED_RESULT, PROVENANCE_UNREVIEWED_RESULT]
#    (the two RESULT-class claims -- c1 DIRECT_RESULT, c2 STATISTICAL_RESULT
#    -- were generated but have author_review_status="pending"; provenance
#    validation correctly refuses to treat generated result-claims as
#    submission-ready until a human marks them reviewed)
```

## What this demonstrates

- Every step is scriptable and non-interactive (`--json`, `--non-interactive`
  where relevant); nothing blocks on a terminal prompt.
- Failures are specific and actionable (`REQ-BIBLIOGRAPHY-FILE-*`,
  `PROVENANCE_UNREVIEWED_RESULT`), not generic "something's wrong".
- Generation is gated on approval (step 4's non-outline call would have
  failed with `GENERATION_PLAN_NOT_APPROVED` had step 3 been skipped).
- Even after successful generation, provenance validation still refuses to
  certify unreviewed result-shaped claims as submission-ready — an agent
  cannot silently promote generated content past a human review gate.

## Continuing from here

To make this fixture's `paperforge provenance validate` pass cleanly, an
agent (or human) would need to: add `references.bib`, add
`data/benchmark_results.csv`, and explicitly mark claims `c1`/`c2`'s
provenance records `author_review_status: "approved"` (there is currently
no CLI command to flip this automatically — provenance records are
reviewed by editing `.paperforge/provenance/<section>.json` directly, a
known gap; see "Remaining limitations" in the release notes).

See [AGENT_PROTOCOL.md](AGENT_PROTOCOL.md) for the full JSON envelope and
exit-code reference, and the
["Using PaperForge with Claude Code, Antigravity, Codex, Cursor, or
another coding agent"](../README.md#using-paperforge-with-claude-code-antigravity-codex-cursor-or-another-coding-agent)
section of the README for the recommended end-to-end agent prompt.
