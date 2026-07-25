# PaperForge Roadmap

## Released

### v0.1.0
Core research dependency engine.
init, capture, doctor (20 checks), impact, build,
review, venues (ieee/acm/neurips), add-claim,
install-hooks, export, status, find.

### v0.2.0
Full command reference documentation.
README updated for all 12 commands.
PyPI package v0.2.0.

### v0.3.0 (this release)
Claim versioning.
paperforge log: full change history for any claim.
paperforge diff: field-level diff against history or experiment.
History recorded automatically by capture, add-claim, doctor --fix.
Rich markup injection fix.

## Planned

### v0.4.0 — Template Library
- Reusable section templates (threat model, experimental setup)
- `paperforge template add --name "threat-model" --from claim_07`
- `paperforge template apply "threat-model"` inserts into new project

### v0.5.0 — Multi-Paper Support
- Shared experiment library across multiple papers
- `paperforge library add exp_01` adds to personal library
- `paperforge library search "accuracy"` finds across all papers

### v0.6.0 — VS Code Extension
- Hover over a number in paper text: see which experiment it came from
- Inline claim status indicators
- Run doctor from the editor

## Non-Goals

These will never be in PaperForge core:
- AI that writes paper content (AI assists, never sources truth)
- Cloud storage of research data
- Replacing Overleaf, Zotero, or MLflow
- A web interface in core (plugins may add this)

See CONSTITUTION.md for the design principles behind these decisions.

## Contributing

See CONTRIBUTING.md to add a venue plugin or new doctor check.
New features must pass the CONSTITUTION.md feature filter.
