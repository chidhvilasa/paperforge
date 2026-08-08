# Requirements engine

`paperforge requirements` evaluates a set of generic `Requirement` rules
against the canonical manifest, combining manifest structure, detected
repository content (e.g. whether a declared bibliography file actually
exists), study-type conditions, and the requested mode
(`outline`/`draft`/`review`/`submission`).

## Command

```bash
paperforge requirements [--mode outline|draft|review|submission] [--json]
                         [--manifest PATH] [--output DIRECTORY]
```

Writes, deterministically ordered by requirement id:

- `.paperforge/requirements.yaml`
- `.paperforge/requirements.json`
- `.paperforge/missing_requirements.md`

## Requirement model

Each `Requirement` has: `id`, `category`, `title`, `description`,
`required`, `status`, `severity`, `source`, `source_locator`,
`validation_rule`, `remediation`, `blocking_modes`, `venue_origin`,
`author_review_required`, `related_fields`.

**Statuses:** `PROVIDED`, `DISCOVERED`, `VERIFIED`, `MISSING`,
`PLACEHOLDER`, `NOT_APPLICABLE`, `CONFLICTING`, `NEEDS_AUTHOR_REVIEW`,
`INACCESSIBLE`, `UNSUPPORTED`.

**Severities:** `ERROR`, `WARNING`, `INFO`.

A requirement `blocks(mode)` only when it is unsatisfied, `required`, and
`mode` is in its `blocking_modes` — so the same rule set can be evaluated
once and filtered per mode.

## Rules implemented

| Rule | Applicable when | Notes |
|---|---|---|
| `REQ-ABSTRACT` | Always | Blocks `review`/`submission` if `abstract` isn't in `manuscript.required_sections` |
| `REQ-BIBLIOGRAPHY` | A claim has `citation_keys`, or `literature.bibliography` is set | `NOT_APPLICABLE` (not an error) when nothing cites anything |
| `REQ-BIBLIOGRAPHY-FILE-*` | `literature.bibliography` paths are set | Checks the file actually exists on disk |
| `REQ-FUNDING-STATEMENT` | Always | "No external funding" is a valid, complete statement — the check is "is a statement present", not "is funding declared" |
| `REQ-DATA-AVAILABILITY` | Always | "Data cannot be shared because ..." is likewise valid and complete |
| `REQ-ETHICS-APPROVAL` | `methodology.participants` is set, or `study_type` suggests human/animal subjects | `NOT_APPLICABLE` otherwise |
| `REQ-INFORMED-CONSENT` | `methodology.participants` is set | `NOT_APPLICABLE` otherwise |
| `REQ-CORRESPONDING-AUTHOR` | Any authors exist | At least one `author.corresponding: true` |
| `REQ-ORCID-*` | Per author | Optional (WARNING) unless the target venue is in a small, explicitly-non-authoritative venue table |
| `REQ-BIOGRAPHY-*` | Per author, only for venues in that same table | Currently only IEEE-family venues |
| `REQ-EVIDENCE-<claim id>` | Claim's `evidence_class` is `DIRECT_RESULT`/`DERIVED_RESULT`/`STATISTICAL_RESULT` | `UNSUPPORTED` + flagged for author review if it has no `evidence_refs`/`citation_keys` |
| `REQ-PLACEHOLDER-<claim id>` | Claim's `evidence_class` is `PLACEHOLDER` | Passes `outline`/`draft`, blocks `submission` |
| `REQ-STATISTICAL-PLAN` | Any claim is `STATISTICAL_RESULT` | Requires `methodology.statistical_plan` to be documented |

None of funding, ethics, consent, DOI, ORCID, statistics, datasets,
figures, or code availability are hardcoded as universally mandatory —
every rule above states its applicability condition first.

## Relationship to Doctor

The requirements engine is independent of, and does not weaken,
`paperforge doctor`'s existing checks (including the v1.6.0
`EVIDENCE_CLASS_*` checks). It is a separate, manifest-centric report; a
project can use either or both.
