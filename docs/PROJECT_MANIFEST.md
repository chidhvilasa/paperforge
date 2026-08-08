# The canonical project manifest (`paperforge.project.yaml`)

`paperforge.project.yaml` is an optional, versioned manifest that describes
a research project's identity, authors, research basis, methodology,
evidence inventory, literature, claims, manuscript plan, declarations, and
submission packaging in one place. It is independent of, and not currently
merged with, the older `.paperforge/paper.yaml` project configuration used
by `init`/`build`/`doctor` (see the rest of this repository's docs for
that workflow).

Schema version: `1.0`. See `paperforge manifest schema` for the full JSON
Schema, generated directly from the Python model
(`src/paperforge/project_manifest/models.py`) so it can never drift out of
sync.

## Top-level sections

| Section | Purpose |
|---|---|
| `schema_version` | Manifest schema version, e.g. `"1.0"` |
| `project` | Title, research domain, study type, language, target venue, deadline, repository URL |
| `authors` | List of authors: id, name, email, orcid, affiliations, corresponding, biography, contribution roles |
| `research` | Problem statement, motivation, primary/secondary questions, hypotheses, objectives, contributions, scope, limitations, future work |
| `methodology` | Study design, datasets, participants, systems, hardware/software, conditions, baselines, metrics, statistical plan, assumptions, threat model, ethics, consent |
| `evidence` | Paths to raw/processed data, canonical results, experiment manifests, benchmarks, notebooks, scripts, figures, tables, source code |
| `literature` | Bibliography path(s), search log, inclusion/exclusion criteria, closest work, novelty statement, reference-verification status |
| `claims` | Individual claims: id, text, evidence_class (see below), evidence_refs, citation_keys, author_review_status |
| `manuscript` | Generation policy, required/optional sections, section order, limits, anonymous review, supplementary material |
| `declarations` | Funding, conflicts of interest, ethics approval, informed consent, data/code availability, author contributions, acknowledgments, AI use |
| `submission` | Cover letter, highlights, graphical abstract, keywords, reviewer suggestions/exclusions, packaging |
| `extensions` | Free-form project-specific data. Always allowed, even in submission mode. |

## Minimum valid manifest

```yaml
schema_version: "1.0"

project:
  title: "Example Research Project"
  research_domain: "Computer Science"
  study_type: "Experimental"
  language: "English"

authors:
  - id: "author_1"
    name: "Alex Morgan"

research:
  primary_question: "What effect does the evaluated method have?"

manuscript:
  generation_policy: "validation_only"
  required_sections:
    - abstract
    - introduction
    - methodology
    - results
    - discussion
    - conclusion
```

That is the *entire* structurally required set. Funding, ethics, consent,
DOI, ORCID, statistical plan, datasets, figures, and code-availability
fields are **never** required by the manifest itself — whether they're
required depends on study type, venue, mode, and declarations, and is
decided by the [requirements engine](REQUIREMENTS_ENGINE.md), not by
`paperforge manifest validate`.

See `examples/minimal_project/paperforge.project.yaml` and
`examples/complete_project/paperforge.project.yaml` for full fictional
examples.

## Commands

```bash
paperforge manifest schema [--output PATH] [--json]
paperforge manifest validate PATH [--mode draft|review|submission] [--json]
paperforge manifest migrate [--input PATH] [--output PATH] [--dry-run] [--yes] [--json]
```

### Validation modes

- `draft` / `review`: unknown fields outside `extensions` are a WARNING,
  unless they look like a likely misspelling of a real field name (e.g.
  `autors` → `authors`, `target_vanue` → `target_venue`), in which case
  they're an ERROR even in draft mode.
- `submission`: every unknown field outside `extensions` is an ERROR,
  misspelled or not.

Every diagnostic — from either mode — carries a stable `code`, a
`field_path`, a human `message`, a `remediation` suggestion, and a
`severity`.

## Safety

- Manifests are loaded with a hardened, size- and depth-bounded safe-YAML
  parser (no arbitrary Python object tags, no duplicate keys, no
  self-referential alias structures, no oversized documents/scalars). See
  [SECURITY_MODEL.md](SECURITY_MODEL.md).
- Any manifest field intended to reference a project-local path is
  resolved through `paperforge.project_manifest.path_safety`, which
  rejects `..` traversal, external absolute paths, Windows drive-letter
  escapes, UNC paths, and symlinks resolving outside the project root.
- Loading or validating a manifest never executes Python, notebooks, shell
  scripts, templates, or configuration hooks found in the project.

## Migrations

`paperforge manifest migrate` detects the manifest's declared
`schema_version`, rejects versions newer than this installation supports,
and applies registered migration steps until the document reaches the
current version. It writes atomically, keeps a `.bak` backup when
overwriting in place, and reports source/output content hashes plus every
transformation applied. See [MIGRATION.md](MIGRATION.md).
