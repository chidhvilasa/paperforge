# Example: agent-driven workflow

A fictional project (`paperforge.project.yaml` in this directory) walking
through the JSON/exit-code agent workflow described in
[docs/AGENT_INTEGRATION.md](../../docs/AGENT_INTEGRATION.md). None of the
content here refers to a real study, author, or institution.

Run these from inside this directory (or pass `--path examples/agent_project`
from the repo root):

```bash
# 1. Validate the manifest (draft mode first -- cheap sanity check)
paperforge manifest validate paperforge.project.yaml --mode draft --json

# 2. See what's missing for a submission
paperforge requirements --mode submission --json
#    -> REQ-BIBLIOGRAPHY-FILE-references.bib will report INACCESSIBLE,
#       since references.bib doesn't exist in this example directory.
#       REQ-CORRESPONDING-AUTHOR, REQ-FUNDING-STATEMENT, and
#       REQ-DATA-AVAILABILITY are already satisfied by this fixture.

# 3. Build and approve a plan
paperforge plan --json
paperforge plan --approve --mode submission --non-interactive --json

# 4. Generate (outline first, to review before anything is "final")
paperforge generate --outline-only --json
paperforge generate --json   # requires the approval from step 3

# 5. Validate provenance
paperforge provenance validate --json
```

Expected outcome at each step is documented inline above. Because this
example intentionally omits `references.bib` and
`data/benchmark_results.csv` (to keep the fixture small), step 2 and later
steps will correctly report specific, actionable gaps rather than a false
"all clear" — that's the requirements engine and provenance validator
doing their job, not a bug in the example.
