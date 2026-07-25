# PaperForge

PaperForge tracks the dependency graph between experiments and
scientific claims so your paper is always internally consistent.

## The Problem

You change one experiment result.
Now you don't know which claims, sections, figures, and tables
need to be updated.

## The Solution

```
$ paperforge impact exp_27

Source: Experiment exp_27
Changed: accuracy 98.4% -> 97.8%

Affected Claims:
claim_07 "EXAMINA achieved 98.4% accuracy."
claim_12 "The proposed system outperforms the B2 baseline..."

Affected Sections:
abstract
results
discussion

Affected Figures:
fig_03

Affected Tables:
tbl_02

Verification Status:
2 claims require verification
1 figure should be reviewed
1 table should be reviewed
```

## Install

```bash
pip install paperforge
# or
uv add paperforge
```

## Philosophy

PaperForge is a compiler, not a writer.

Research data goes in. A consistent, submission-ready paper
comes out. AI drafting is one optional stage at the end,
not the foundation.

See CONSTITUTION.md for design principles.

## Status

v0.1.0 — active development. Not production ready.

## License

MIT
