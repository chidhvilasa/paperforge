# PaperForge Constitution

Every pull request must be evaluated against these principles.
If a feature does not strengthen the dependency graph,
it does not belong in core.

## Purpose

PaperForge is a research dependency engine.

Its purpose is to maintain traceability, consistency, and
reproducibility between research evidence and published claims.

## Principles

1.  Research is the source. The paper is the compiled artifact.
2.  Every published claim must trace to evidence and be fully
    explainable from that evidence.
3.  Every change must propagate through the dependency graph.
4.  Deterministic validation is preferred over AI.
5.  AI assists. It never becomes the source of truth.
6.  Simplicity is preferred over feature count.
7.  Existing research tools are integrated, not replaced.
8.  Every feature must strengthen the dependency graph.
9.  All user research data is stored locally. No external calls
    for user data. No cloud storage.
10. Every feature must work fully offline.

## Feature Filter

Before implementing any feature, answer all four:
  Does it strengthen the dependency graph?
  Does it improve traceability?
  Does it improve consistency or reproducibility?
  Does it work offline with no external API calls?

If any answer is no, the feature belongs in a plugin or not at all.
