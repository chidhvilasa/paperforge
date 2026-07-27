"""paperforge import command."""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

console = Console()


def _strip_markdown_formatting(raw: str) -> list[tuple[str, bool]]:
    """
    Parses Markdown content into (paragraph_text, is_contribution) tuples.
    Filters out HTML comments and header titles.
    """
    clean_raw = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)
    lines = clean_raw.splitlines()

    paragraphs: list[tuple[str, bool]] = []
    current_para: list[str] = []
    in_contributions_section = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith(("##", "#")):
            if current_para:
                text = " ".join(current_para).strip()
                if text:
                    paragraphs.append((text, False))
                current_para = []

            header_title = stripped.lstrip("#").strip().lower()
            in_contributions_section = "contribution" in header_title
            continue

        if stripped.startswith(("- ", "* ")):
            item_text = stripped[2:].strip()
            if item_text:
                is_contrib = in_contributions_section
                paragraphs.append((item_text, is_contrib))
            continue

        if not stripped:
            if current_para:
                text = " ".join(current_para).strip()
                if text:
                    paragraphs.append((text, False))
                current_para = []
            continue

        current_para.append(stripped)

    if current_para:
        text = " ".join(current_para).strip()
        if text:
            paragraphs.append((text, False))

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

    info_dir = project_root / "paper_information"
    if not info_dir.exists():
        console.print(
            "[yellow]paper_information/ directory not found.[/yellow]"
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

    # STEP C — Import content/*.md sections
    content_dir = info_dir / "content"
    claims_dir = pf_dir / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)

    existing_claim_files = list(claims_dir.glob("*.yaml"))
    existing_ids: set[str] = set()
    existing_prefixes: set[str] = set()

    for cf in existing_claim_files:
        cdata = yaml.safe_load(cf.read_text(encoding="utf-8")) or {}
        cid = cdata.get("id", cf.stem)
        existing_ids.add(cid)
        ctext = (cdata.get("text") or "").strip().lower()[:80]
        if ctext:
            existing_prefixes.add(ctext)

    claim_counter = 1

    def get_next_id() -> str:
        nonlocal claim_counter
        while f"claim_{claim_counter:02d}" in existing_ids:
            claim_counter += 1
        cid = f"claim_{claim_counter:02d}"
        existing_ids.add(cid)
        return cid

    section_results: dict[str, tuple[int, int]] = {}

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
            new_contrib_cnt = 0

            for para_text, is_contrib in parsed_paras:
                norm_prefix = para_text.strip().lower()[:80]
                if norm_prefix in existing_prefixes and not force:
                    continue

                new_cid = get_next_id()
                cdata = {
                    "id": new_cid,
                    "text": para_text,
                    "experiment": "",
                    "experiments": [],
                    "figures": [],
                    "tables": [],
                    "citations": [],
                    "sections": [sec_name],
                    "status": "unverified",
                    "last_verified": None,
                    "subsection": "",
                    "algorithms": [],
                    "is_contribution": is_contrib,
                    "compared_work": "",
                }
                (claims_dir / f"{new_cid}.yaml").write_text(
                    yaml.dump(cdata, default_flow_style=False, allow_unicode=True),
                    encoding="utf-8",
                )
                existing_prefixes.add(norm_prefix)
                new_claims_cnt += 1
                if is_contrib:
                    new_contrib_cnt += 1

            section_results[sec_name] = (new_claims_cnt, new_contrib_cnt)

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
        Text("Sections imported:"),
    ]

    for sname, (n_claims, n_contrib) in section_results.items():
        contrib_str = f", {n_contrib} contribution claims" if n_contrib > 0 else ""
        lines.append(Text(f"  {sname}:  {n_claims} new claims{contrib_str}"))

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
            title="Import Complete",
            border_style="green",
        )
    )
