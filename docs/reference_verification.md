# `paperforge references`

The `paperforge references` command validates BibTeX citation entries in `.paperforge/citations/` for completeness and accuracy, with optional online DOI lookup via Crossref API.

## Usage

```bash
paperforge references [OPTIONS]
```

## Options

- `-p, --path PATH`: Project root directory (default: current directory).
- `--online`: Enable online verification against Crossref API for DOIs. Results are cached locally in `.paperforge/cache/crossref_cache.json`.

## What Reference Verification Checks

1. **Local Bibliographic Validation**:
   - Ensures title, authors, venue, and publication year are present.
   - Detects `TODO` stubs or unconfirmed citation notes (`CITATION_NO_TITLE`, `CITATION_HAS_INTERNAL_NOTE`).
2. **Crossref API DOI Matching (`--online`)**:
   - Queries Crossref API (`api.crossref.org`) using article DOI.
   - Compares local title and author metadata against official publisher records.
   - Flags discrepancies as `REFERENCE_METADATA_MISMATCH` (WARNING).

## Generated Reports

- `paper_generated/reports/reference_verification.md`
- `.paperforge/cache/crossref_cache.json`
