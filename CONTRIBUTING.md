# Contributing to PaperForge

Thank you for contributing to PaperForge.

## Before You Start

Read [CONSTITUTION.md](CONSTITUTION.md).

Every feature must pass this filter:
- Does it strengthen the dependency graph?
- Does it improve traceability, consistency, or reproducibility?
- Does it work fully offline?
- Does it avoid storing user data outside the local project?

If any answer is no, the feature belongs in a plugin or not at all.

## Setup

```bash
git clone https://github.com/chidhvilasa/paperforge
cd paperforge
uv sync
uv run pytest
```

All tests must pass before you start.

## Development Workflow

1. Create a branch: `git checkout -b feat/your-feature`
2. Write tests first.
3. Implement the feature.
4. Run the full verification suite (see below).
5. Open a pull request against `main`.

## Verification Suite

Run all of these before opening a PR. All must pass:

```bash
uv run pytest tests/ -v
uv run ruff check src/ tests/
uv run mypy src/
uv run paperforge --version
```

## Adding a Venue Plugin

Venue plugins are the designed extension point.
Do not modify core code to add a venue.

1. Create `src/paperforge/venues/your_venue.py`
2. Implement `VenuePlugin` (see `venues/base.py`)
3. Register in `venues/registry.py`
4. Add tests in `tests/test_venues.py`
5. Update `CHANGELOG.md`

See `venues/ieee.py` for a complete example.

## Pull Request Rules

- All tests must pass.
- ruff and mypy must pass with zero errors.
- Every new command needs tests.
- Every new venue plugin needs at least 3 tests.
- Update CHANGELOG.md under [Unreleased].
- Do not modify CONSTITUTION.md without discussion.

## What We Do Not Accept

- Features that require internet access in core.
- Features that store user data outside `.paperforge/`.
- AI-generated content as a source of truth anywhere.
- New dependencies without discussion.
- Anything that weakens the dependency graph model.
