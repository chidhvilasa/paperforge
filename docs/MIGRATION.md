# Manifest schema migrations

`paperforge manifest migrate` upgrades a `paperforge.project.yaml`
declaring an older `schema_version` to the current one
(`paperforge.project_manifest.models.CURRENT_SCHEMA_VERSION`, `"1.0"` as
of this release).

## Command

```bash
paperforge manifest migrate [--input PATH] [--output PATH]
                             [--dry-run] [--yes] [--json]
```

- `--input` defaults to `paperforge.project.yaml` in the current directory.
- `--output` defaults to overwriting `--input` in place (a `.bak` copy of
  the original is written first).
- `--dry-run` reports what would change without writing anything.
- `--yes` skips the interactive overwrite confirmation (always skipped
  automatically under `--json`).

## What it reports

Every migration run produces a report containing:

- `source_version` / `target_version`
- `applied_steps` — the exact chain of version transitions applied
- `transformations` — a human-readable description of each step
- `unresolved_conflicts` — populated (never silently dropped) if no
  registered migration path exists from the detected version
- `source_hash` / `output_hash` — SHA-256 of the canonicalized YAML before
  and after, so you can verify exactly how much changed

A manifest already at the current version is a no-op (reported as
`"already at the current schema version"`, not an error).

## What's registered today

One real migration ships: a synthetic legacy `"0.1"` flat layout (used to
prove the registry mechanism end-to-end, not a format any released
version of PaperForge ever produced) to `"1.0"`. It exists so the
migration *mechanism* — version detection, atomic writes, backups,
hashing, reporting — is real and tested, and so future schema changes
have a stable place to add a new `MigrationStep` without redesigning
anything.

A manifest declaring a version **newer** than this installation's
`CURRENT_SCHEMA_VERSION` is rejected outright
(`UnsupportedSchemaVersionError` / exit code 11) rather than guessed at or
partially applied.

## Safety

- Atomic writes throughout (`paperforge.utils.atomic`) — a crash mid-write
  never corrupts the manifest.
- The original is preserved as a `.bak` file when migrating in place.
- Migration reuses the same hardened safe-YAML loader as
  `paperforge manifest validate` (see [SECURITY_MODEL.md](SECURITY_MODEL.md)).
