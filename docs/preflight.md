# `paperforge preflight`

The `paperforge preflight` command executes an automated visual rendering, bounding box overlap, text artifact scanning, template fingerprinting, and structural integrity analysis on the compiled PDF manuscript.

## Usage

```bash
paperforge preflight [OPTIONS]
```

## Options

- `-p, --path PATH`: Project root directory (default: current directory).
- `-m, --mode [draft|submission]`: Preflight inspection mode (`draft` or `submission`).
- `--pdf PATH`: Path to custom compiled PDF file to inspect.
- `--json`: Output full preflight report as a JSON object.
- `--open-renders`: Automatically open the rendered PNG page images directory in the file manager.

## What Preflight Checks

1. **Page Image Rendering (`pdf_pages/page-XXX.png`)**:
   Renders every page of the compiled PDF at high resolution (150 DPI) using PyMuPDF (`fitz`).
2. **Template Fingerprinting (`venue_fingerprint.json`)**:
   Verifies that the compiled document class and required structure match the target venue manifest (`ieee`, `ieee_access`, `acm`, `neurips`).
3. **Visual Overlap & Bounding Box Scan (`PDF_OBJECT_OVERLAP`)**:
   Performs exact rectangle intersection analysis on text and float bounding boxes to catch overlapping text, title overlaps, and Index Terms overlapping Introduction headings.
4. **Text Artifact & Escaping Scan (`PDF_TEXT_ARTIFACT`)**:
   Scans rendered text for unparsed LaTeX commands (`\textbf`, `\texttt`), tab corruption (`extbf{`, `exttt{`), unresolved references (`[?]`, `??`), placeholders, and malformed percentages (`73.6At`).
5. **Structural Integrity & Outline (`SECTION_ROADMAP_MISMATCH`, `FLOAT_AFTER_CONCLUSION`)**:
   Verifies section roadmap consistency, ensures floats do not drift after Conclusion, and resolves symbolic references (`{{section:id}}`, `{{figure:id}}`, `{{table:id}}`).

## Generated Reports

Preflight outputs persistent reports to `paper_generated/reports/`:
- `pdf_preflight.md` & `pdf_preflight.json`
- `pdf_pages/page-001.png`, `page-002.png`, ...
- `venue_fingerprint.md` & `venue_fingerprint.json`
- `structural_integrity.md` & `structural_integrity.json`
