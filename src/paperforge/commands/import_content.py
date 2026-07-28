"""paperforge import command."""

from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from paperforge.core.project import PaperForgeProject

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def _paragraph_hash(text: str) -> str:
    """Compute a canonical 12-char MD5 hash for deduplication.

    Strips whitespace, lowercases, takes first 120 chars.
    """
    canonical = " ".join(text.lower().split())[:120]
    return hashlib.md5(canonical.encode()).hexdigest()[:12]


def _strip_markdown_formatting(raw: str) -> list[tuple[str, bool, str]]:
    """Parses Markdown content into (paragraph_text, is_contribution, subsection) tuples.

    Filters out HTML comments and main section header titles.
    """
    clean_raw = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)
    lines = clean_raw.splitlines()

    paragraphs: list[tuple[str, bool, str]] = []
    current_para: list[str] = []
    in_contributions_section = False
    current_subsection = ""

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("## ") and not stripped.startswith("### "):
            if current_para:
                text = " ".join(current_para).strip()
                if text:
                    paragraphs.append((text, False, current_subsection))
                current_para = []

            sub_title = stripped.lstrip("#").strip()
            header_title_lower = sub_title.lower()
            in_contributions_section = "contribution" in header_title_lower
            if "contribution" not in header_title_lower:
                current_subsection = sub_title
            continue
        elif stripped.startswith("#"):
            if current_para:
                text = " ".join(current_para).strip()
                if text:
                    paragraphs.append((text, False, current_subsection))
                current_para = []
            header_title_lower = stripped.lstrip("#").strip().lower()
            in_contributions_section = "contribution" in header_title_lower
            current_subsection = ""
            continue

        if stripped.startswith(("- ", "* ")):
            item_text = stripped[2:].strip()
            if item_text:
                is_contrib = in_contributions_section
                paragraphs.append((item_text, is_contrib, current_subsection))
            continue

        if not stripped:
            if current_para:
                text = " ".join(current_para).strip()
                if text:
                    paragraphs.append((text, False, current_subsection))
                current_para = []
            continue

        current_para.append(stripped)

    if current_para:
        text = " ".join(current_para).strip()
        if text:
            paragraphs.append((text, False, current_subsection))

    return paragraphs


def run(
    project_root: Path,
    section: str | None = None,
    force: bool = False,
) -> None:
    pf_dir = project_root / ".paperforge"
    if not pf_dir.exists():
        console.print(
            "[red]Not a PaperForge project. Run `paperforge init` first.[/red]"
        )
        sys.exit(1)

    project = PaperForgeProject.load(project_root)
    info_dir = project_root / project.config.paper_information_dir
    if not info_dir.exists():
        alt_info_dir = project_root / "paper_information"
        if alt_info_dir.exists():
            info_dir = alt_info_dir
        else:
            console.print(
                f"[yellow]{info_dir} directory not found.[/yellow]"
            )

    paper_yaml_path = pf_dir / "paper.yaml"
    paper_data: dict[str, Any] = {}
    if paper_yaml_path.exists():
        paper_data = yaml.safe_load(paper_yaml_path.read_text(encoding="utf-8")) or {}

    metadata_updated = False
    author_updated = False

    # STEP A — Import metadata.yaml
    meta_file = info_dir / "metadata.yaml"
    if meta_file.exists():
        meta_data = yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
        for key, val in meta_data.items():
            if (
                val is not None
                and val != ""
                and (force or not paper_data.get(key) or paper_data.get(key) != val)
            ):
                paper_data[key] = val
                metadata_updated = True

    # STEP B — Import author.yaml
    author_file = info_dir / "author.yaml"
    if author_file.exists():
        author_data = yaml.safe_load(author_file.read_text(encoding="utf-8")) or {}
        authors_list = author_data.get("authors", [])
        if authors_list:
            author_names = [
                a["name"] for a in authors_list if isinstance(a, dict) and a.get("name")
            ]
            affiliations = []
            for a in authors_list:
                if isinstance(a, dict):
                    affiliations.append(
                        {
                            "name": a.get("name", ""),
                            "institution": a.get("institution", ""),
                            "department": a.get("department", ""),
                            "city": a.get("city", ""),
                            "country": a.get("country", ""),
                            "email": a.get("email", ""),
                            "membership": a.get("membership", ""),
                            "shared_with": a.get("shared_with") or [],
                        }
                    )
                    if a.get("corresponding"):
                        if a.get("email"):
                            paper_data["email"] = a["email"]
                        if a.get("orcid"):
                            paper_data["orcid"] = a["orcid"]

            if author_names:
                paper_data["authors"] = author_names
                paper_data["affiliations"] = affiliations
                author_updated = True

    if metadata_updated or author_updated:
        paper_yaml_path.write_text(
            yaml.dump(paper_data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )

    # STEP C — Import content/*.md sections (MERGE MODE)
    content_dir = info_dir / "content"
    claims_dir = pf_dir / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)
    citations_dir = pf_dir / "citations"

    existing_claim_files = list(claims_dir.glob("*.yaml"))
    existing_ids: set[str] = set()
    # hash → (claim_id, claim_filepath)
    existing_hashes: dict[str, tuple[str, Path]] = {}

    for cf in existing_claim_files:
        cdata = yaml.safe_load(cf.read_text(encoding="utf-8")) or {}
        cid = cdata.get("id", cf.stem)
        existing_ids.add(cid)
        # Index by import_hash if stored
        stored_hash = cdata.get("import_hash", "")
        if stored_hash:
            existing_hashes[stored_hash] = (cid, cf)
        else:
            # Back-compute hash from text for legacy claims
            ctext = (cdata.get("text") or "").strip()
            if ctext:
                h = _paragraph_hash(ctext)
                if h not in existing_hashes:
                    existing_hashes[h] = (cid, cf)

    claim_counter = 1

    def get_next_id() -> str:
        nonlocal claim_counter
        while f"claim_{claim_counter:02d}" in existing_ids:
            claim_counter += 1
        cid = f"claim_{claim_counter:02d}"
        existing_ids.add(cid)
        return cid

    section_results: dict[str, tuple[int, int, int]] = {}  # (new, updated, contrib)
    citation_pattern = re.compile(r"\[([a-z][a-zA-Z0-9]+\d{4}[a-z]?)\]")
    imported_claims_list: list[dict[str, Any]] = []

    if content_dir.exists():
        sec_files = sorted(content_dir.glob("*.md"))
        target_section = section.replace(".md", "") if section else None

        for sf in sec_files:
            sec_name = sf.stem
            if target_section and sec_name != target_section:
                continue

            raw_text = sf.read_text(encoding="utf-8")
            parsed_paras = _strip_markdown_formatting(raw_text)

            new_claims_cnt = 0
            updated_claims_cnt = 0
            new_contrib_cnt = 0

            for para_text, is_contrib, sub_hdr in parsed_paras:
                h = _paragraph_hash(para_text)

                # Parse [citation-key] notation
                found_keys = citation_pattern.findall(para_text)
                valid_keys: list[str] = []
                for key in found_keys:
                    cit_path = citations_dir / f"{key}.yaml"
                    if cit_path.exists():
                        if key not in valid_keys:
                            valid_keys.append(key)
                    else:
                        console.print(
                            f"[yellow]Citation [{key}] not found in "
                            f".paperforge/citations/ -- skipped.[/yellow]"
                        )

                clean_text = citation_pattern.sub("", para_text).strip()

                if h in existing_hashes:
                    # MERGE: claim already exists
                    existing_cid, existing_cf = existing_hashes[h]
                    if force:
                        # --force: UPDATE the matched claim's text and metadata
                        existing_cdata = yaml.safe_load(
                            existing_cf.read_text(encoding="utf-8")
                        ) or {}
                        existing_cdata["text"] = clean_text
                        existing_cdata["sections"] = list(
                            set(existing_cdata.get("sections", []) + [sec_name])
                        )
                        existing_cdata["subsection"] = sub_hdr or existing_cdata.get(
                            "subsection", ""
                        )
                        existing_cdata["import_hash"] = h
                        if valid_keys:
                            existing_cdata["citations"] = valid_keys
                        existing_cf.write_text(
                            yaml.dump(
                                existing_cdata,
                                default_flow_style=False,
                                allow_unicode=True,
                            ),
                            encoding="utf-8",
                        )
                        updated_claims_cnt += 1
                    # If not force: skip (already exists — no duplicate created)
                    continue

                # No match: CREATE new claim with import_hash
                new_cid = get_next_id()
                cdata = {
                    "id": new_cid,
                    "text": clean_text,
                    "experiment": "",
                    "experiments": [],
                    "figures": [],
                    "tables": [],
                    "citations": valid_keys,
                    "sections": [sec_name],
                    "status": "unverified",
                    "last_verified": None,
                    "subsection": sub_hdr,
                    "algorithms": [],
                    "is_contribution": is_contrib,
                    "compared_work": "",
                    "is_math": False,
                    "raw_latex": False,
                    "claim_type": "claim",
                    "import_hash": h,
                }
                (claims_dir / f"{new_cid}.yaml").write_text(
                    yaml.dump(cdata, default_flow_style=False, allow_unicode=True),
                    encoding="utf-8",
                )
                # Register hash so subsequent paragraphs in same run don't duplicate
                existing_hashes[h] = (new_cid, claims_dir / f"{new_cid}.yaml")
                new_claims_cnt += 1
                if is_contrib:
                    new_contrib_cnt += 1
                imported_claims_list.append(cdata)

            section_results[sec_name] = (new_claims_cnt, updated_claims_cnt, new_contrib_cnt)

    # STEP D — Import graphs/*.py
    graphs_dir = info_dir / "graphs"
    graph_scripts_run = 0
    graph_scripts_failed = 0

    if graphs_dir.exists():
        for gf in sorted(graphs_dir.glob("*.py")):
            graph_scripts_run += 1
            res = subprocess.run(
                [sys.executable, str(gf)],
                capture_output=True,
                text=True,
                cwd=project_root,
                check=False,
            )
            if res.returncode != 0:
                graph_scripts_failed += 1

    # STEP E — Import tables/*.csv
    tables_info_dir = info_dir / "tables"
    tables_pf_dir = pf_dir / "tables"
    tables_pf_dir.mkdir(parents=True, exist_ok=True)
    imported_tables_cnt = 0

    if tables_info_dir.exists():
        for csv_file in sorted(tables_info_dir.glob("*.csv")):
            tbl_stem = csv_file.stem
            tbl_id = tbl_stem
            tbl_yaml_path = tables_pf_dir / f"{tbl_stem}.yaml"
            if tbl_yaml_path.exists() and not force:
                continue

            try:
                with open(csv_file, encoding="utf-8") as f:
                    reader = list(csv.reader(f))
                if reader:
                    headers = reader[0]
                    data_rows = reader[1:]
                    tbl_data = {
                        "id": tbl_id,
                        "caption": f"Table: {tbl_stem}",
                        "columns": headers,
                        "rows": data_rows,
                        "notes": "",
                        "first_mentioned_in": None,
                        "source_experiment": None,
                        "wide": False,
                        "auto_rows_from_experiment": None,
                        "is_math": False,
                        "raw_latex_rows": False,
                    }
                    tbl_yaml_path.write_text(
                        yaml.dump(
                            tbl_data, default_flow_style=False, allow_unicode=True
                        ),
                        encoding="utf-8",
                    )
                    imported_tables_cnt += 1
            except (OSError, csv.Error) as e:
                console.print(f"[dim]Failed to import CSV {csv_file.name}: {e}[/dim]")

    # Print summary panel
    lines = [
        Text(f"metadata.yaml:  {'updated' if metadata_updated else 'skipped/up-to-date'}"),
        Text(f"author.yaml:    {'updated' if author_updated else 'skipped/up-to-date'}"),
        Text(""),
        Text("Sections imported (merge mode):"),
    ]

    for sname, (n_new, n_updated, n_contrib) in section_results.items():
        contrib_str = f", {n_contrib} contribution" if n_contrib > 0 else ""
        updated_str = f", {n_updated} updated" if n_updated > 0 else ""
        lines.append(
            Text(f"  {sname}:  {n_new} new claims{updated_str}{contrib_str}")
        )

    lines.append(Text(""))
    lines.append(
        Text(
            f"Graphs executed: {graph_scripts_run} script(s)"
            + (f" ({graph_scripts_failed} failed)" if graph_scripts_failed else "")
        )
    )
    lines.append(Text(f"Tables imported: {imported_tables_cnt} new table(s)"))
    lines.append(Text(""))
    lines.append(Text("Next steps:"))
    lines.append(Text("  1. Link claims to experiments: edit .paperforge/claims/*.yaml"))
    lines.append(Text("  2. Add citation keys to claims: edit citations: [] field"))
    lines.append(Text("  3. Run: paperforge doctor"))
    lines.append(Text("  4. Run: paperforge build"))

    console.print(
        Panel(
            Text("\n").join(lines),
            title="Import Complete (Merge Mode)",
            border_style="green",
        )
    )

    orphan_count = sum(1 for c in imported_claims_list if not c.get("experiment"))
    if orphan_count > 0:
        console.print(
            f"[yellow]{orphan_count} imported claims have no linked "
            "experiment. Link them manually in .paperforge/claims/ "
            "or use: paperforge doctor to find ORPHAN_CLAIM issues.[/yellow]"
        )
