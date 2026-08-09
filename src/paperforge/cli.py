"""PaperForge command-line interface."""

from collections.abc import Callable
from pathlib import Path

import typer

from paperforge import __version__

app = typer.Typer(
    name="paperforge",
    help="A research dependency engine that tracks the graph between "
    "experiments and scientific claims.",
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"paperforge {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version_flag: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the paperforge version and exit.",
    ),
) -> None:
    """PaperForge: a research dependency engine."""


@app.command()
def init(
    path: Path = typer.Argument(
        default=Path("."),
        help="Directory to initialize. Defaults to current directory.",
    ),
) -> None:
    """Initialize PaperForge in a research project directory."""
    from paperforge.commands.init import run

    run(path.resolve())


@app.command()
def inspect(
    path: Path = typer.Argument(
        default=Path("."),
        help="Directory to inspect. Defaults to current directory.",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of a console panel."
    ),
) -> None:
    """Read-only reconnaissance of a directory before intake or import.

    Detects existing manuscripts, bibliography, figures, tables,
    notebooks, data files, venue template files, package managers, Git
    state, likely secrets, and absolute local paths. Never modifies or
    executes anything it finds.
    """
    from paperforge.commands.inspect import run

    run(project_root=path.resolve(), json_output=json_output)


manifest_app = typer.Typer(
    name="manifest",
    help="Work with the canonical paperforge.project.yaml manifest.",
)
app.add_typer(manifest_app, name="manifest")


@manifest_app.command("schema")
def manifest_schema(
    output: Path | None = typer.Option(
        None, "--output", help="Write the JSON Schema document to this path."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Wrap the schema in the standard JSON result envelope."
    ),
) -> None:
    """Print (or save) the JSON Schema for paperforge.project.yaml."""
    from paperforge.commands.manifest_cmd import run_schema

    raise typer.Exit(code=run_schema(output=output, json_output=json_output))


@manifest_app.command("validate")
def manifest_validate(
    path: Path = typer.Argument(
        default=Path("paperforge.project.yaml"), help="Path to the manifest file."
    ),
    mode: str = typer.Option(
        "draft", "--mode", "-m", help="Validation mode: draft, review, or submission."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Validate a manifest file (safe YAML, structure, unknown fields)."""
    from paperforge.commands.manifest_cmd import run_validate

    raise typer.Exit(
        code=run_validate(path.resolve(), mode=mode, json_output=json_output)
    )


@manifest_app.command("migrate")
def manifest_migrate(
    input_path: Path = typer.Option(
        Path("paperforge.project.yaml"), "--input", help="Manifest file to migrate."
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Write the migrated manifest here instead of overwriting --input.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Report what would change without writing."
    ),
    yes: bool = typer.Option(
        False, "--yes", help="Do not prompt before overwriting in place."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Migrate a manifest to the current schema version."""
    from paperforge.commands.manifest_cmd import run_migrate

    raise typer.Exit(
        code=run_migrate(
            input_path=input_path.resolve(),
            output_path=output.resolve() if output else None,
            dry_run=dry_run,
            yes=yes,
            json_output=json_output,
        )
    )


@app.command()
def requirements(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    manifest: Path | None = typer.Option(
        None,
        "--manifest",
        help="Manifest path. Defaults to <path>/paperforge.project.yaml.",
    ),
    mode: str = typer.Option(
        "draft", "--mode", "-m", help="outline, draft, review, or submission."
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Directory to write reports to. Defaults to <path>/.paperforge.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Evaluate mode-aware manuscript requirements against the project manifest."""
    from paperforge.commands.requirements_cmd import run as run_requirements

    root = path.resolve()
    raise typer.Exit(
        code=run_requirements(
            project_root=root,
            manifest_path=manifest.resolve() if manifest else None,
            mode=mode,
            json_output=json_output,
            output_dir=output.resolve() if output else None,
        )
    )


@app.command()
def plan(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    manifest: Path | None = typer.Option(
        None,
        "--manifest",
        help="Manifest path. Defaults to <path>/paperforge.project.yaml.",
    ),
    section: str | None = typer.Option(
        None, "--section", help="Show only this section."
    ),
    refresh: bool = typer.Option(
        False,
        "--refresh",
        help="No-op: the plan is always rebuilt fresh from the current manifest.",
    ),
    approve: bool = typer.Option(
        False, "--approve", help="Record approval of the current plan."
    ),
    revoke_approval: bool = typer.Option(
        False, "--revoke-approval", help="Revoke any existing approval."
    ),
    mode: str = typer.Option(
        "submission", "--mode", "-m", help="Mode the approval is recorded for."
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Do not prompt; approver is recorded as 'agent'.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Build a structural, approval-gated generation plan (no manuscript prose)."""
    from paperforge.commands.plan_cmd import run as run_plan

    _ = refresh
    raise typer.Exit(
        code=run_plan(
            project_root=path.resolve(),
            manifest_path=manifest.resolve() if manifest else None,
            section=section,
            approve=approve,
            revoke_approval=revoke_approval,
            mode=mode,
            json_output=json_output,
            non_interactive=non_interactive,
        )
    )


@app.command()
def generate(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    manifest: Path | None = typer.Option(
        None,
        "--manifest",
        help="Manifest path. Defaults to <path>/paperforge.project.yaml.",
    ),
    all_sections: bool = typer.Option(
        True, "--all/--not-all", help="Generate every planned section (default)."
    ),
    section: str | None = typer.Option(
        None, "--section", help="Generate only this section."
    ),
    regenerate: str | None = typer.Option(
        None, "--regenerate", help="Regenerate only this section."
    ),
    outline_only: bool = typer.Option(
        False,
        "--outline-only",
        help="Structural outline only (headings/goals/permitted claims). No prose, no approval required.",
    ),
    draft_with_placeholders: bool = typer.Option(
        False,
        "--draft-with-placeholders",
        help="Watermarked draft including placeholder claims. No approval required. Fails submission mode.",
    ),
    no_ai: bool = typer.Option(
        True,
        "--no-ai/--ai",
        help="Use the deterministic no-AI provider (default; the only provider that ships).",
    ),
    provider: str = typer.Option(
        "no_ai", "--provider", help="Generation provider: no_ai or fixture."
    ),
    review_existing: bool = typer.Option(
        False,
        "--review-existing",
        help="List already-generated sections instead of generating.",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Never prompt (this command never prompts regardless).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Deterministically generate manuscript section content from an approved plan."""
    from paperforge.commands.generate_cmd import run as run_generate

    _ = all_sections  # generating "all" planned sections is the default when no --section/--regenerate given
    effective_provider = provider if provider != "no_ai" or no_ai else "no_ai"
    raise typer.Exit(
        code=run_generate(
            project_root=path.resolve(),
            manifest_path=manifest.resolve() if manifest else None,
            section=section,
            regenerate=regenerate,
            outline_only=outline_only,
            draft_with_placeholders=draft_with_placeholders,
            provider_name=effective_provider,
            review_existing=review_existing,
            non_interactive=non_interactive,
            json_output=json_output,
        )
    )


provenance_app = typer.Typer(
    name="provenance", help="Inspect and validate generation provenance sidecars."
)
app.add_typer(provenance_app, name="provenance")


@provenance_app.command("show")
def provenance_show(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Show recorded provenance for generated sections."""
    from paperforge.commands.provenance_cmd import run_show

    raise typer.Exit(
        code=run_show(project_root=path.resolve(), json_output=json_output)
    )


@provenance_app.command("validate")
def provenance_validate(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    manifest: Path | None = typer.Option(None, "--manifest", help="Manifest path."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Validate provenance: staleness, missing claims/evidence, unreviewed results, placeholders."""
    from paperforge.commands.provenance_cmd import run_validate

    raise typer.Exit(
        code=run_validate(
            project_root=path.resolve(),
            manifest_path=manifest.resolve() if manifest else None,
            json_output=json_output,
        )
    )


@provenance_app.command("export")
def provenance_export(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    output: Path | None = typer.Option(
        None, "--output", help="Write exported provenance JSON here."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Export the full provenance index and records as JSON."""
    from paperforge.commands.provenance_cmd import run_export

    raise typer.Exit(
        code=run_export(
            project_root=path.resolve(),
            output=output.resolve() if output else None,
            json_output=json_output,
        )
    )


evidence_app = typer.Typer(
    name="evidence",
    help="Direct/derived/statistical evidence backing DIRECT_RESULT, "
    "DERIVED_RESULT, and STATISTICAL_RESULT claims.",
)
app.add_typer(evidence_app, name="evidence")

evidence_direct_app = typer.Typer(
    name="direct", help="Values read verbatim from a source, or recorded manually."
)
evidence_app.add_typer(evidence_direct_app, name="direct")

evidence_derived_app = typer.Typer(
    name="derived", help="Values computed from other evidence by a safe formula."
)
evidence_app.add_typer(evidence_derived_app, name="derived")

evidence_statistical_app = typer.Typer(
    name="statistical", help="Explicitly recorded statistical results."
)
evidence_app.add_typer(evidence_statistical_app, name="statistical")


@evidence_direct_app.command("add")
def evidence_direct_add(
    evidence_id: str = typer.Option(..., "--id", help="Unique evidence id."),
    type_: str = typer.Option(
        "manual", "--type", help="csv, json, yaml, or manual."
    ),
    source_path: str = typer.Option(
        "", "--source-path", help="Project-relative path to the source file."
    ),
    source_locator: str = typer.Option(
        "",
        "--source-locator",
        help="csv: 'row=0;col=name'. json/yaml: dotted path, e.g. 'results.latency.mean'.",
    ),
    value: str | None = typer.Option(
        None, "--value", help="Value for type=manual (required in that case)."
    ),
    value_type: str = typer.Option(
        "number", "--value-type", help="number, string, or bool."
    ),
    unit: str = typer.Option("", "--unit", help="Unit string, e.g. 'ms', 'percent'."),
    sample_size: int | None = typer.Option(None, "--sample-size"),
    observations_count: int | None = typer.Option(None, "--observations-count"),
    notes: str = typer.Option("", "--notes"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Record a direct-evidence value (from a CSV/JSON/YAML source, or manual)."""
    from paperforge.commands.evidence_cmd import run_direct_add

    raise typer.Exit(
        code=run_direct_add(
            project_root=path.resolve(),
            evidence_id=evidence_id,
            source_type=type_,
            source_path=source_path,
            source_locator=source_locator,
            value=value,
            value_type=value_type,
            unit=unit,
            sample_size=sample_size,
            observations_count=observations_count,
            notes=notes,
            json_output=json_output,
        )
    )


@evidence_direct_app.command("validate")
def evidence_direct_validate(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Validate all recorded direct evidence (structure + source staleness)."""
    from paperforge.commands.evidence_cmd import run_validate

    raise typer.Exit(
        code=run_validate(project_root=path.resolve(), kind="direct", json_output=json_output)
    )


@evidence_derived_app.command("add")
def evidence_derived_add(
    evidence_id: str = typer.Option(..., "--id", help="Unique evidence id."),
    formula: str = typer.Option(
        ..., "--formula", help="Safe expression, e.g. '(baseline - adaptive) / baseline * 100'."
    ),
    operands: str = typer.Option(
        "", "--operands", help="Comma-separated evidence ids referenced by the formula."
    ),
    unit: str = typer.Option("", "--unit"),
    precision: int | None = typer.Option(
        None, "--precision", help="Round the result to this many decimal digits."
    ),
    rounding: str = typer.Option(
        "half_up", "--rounding", help="half_up, half_even, floor, ceil, or none."
    ),
    notes: str = typer.Option("", "--notes"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Compute and record a derived-evidence value with the safe formula evaluator."""
    from paperforge.commands.evidence_cmd import run_derived_add

    operand_ids = [o.strip() for o in operands.split(",") if o.strip()]
    raise typer.Exit(
        code=run_derived_add(
            project_root=path.resolve(),
            evidence_id=evidence_id,
            formula=formula,
            operand_ids=operand_ids,
            unit=unit,
            precision=precision,
            rounding=rounding,
            notes=notes,
            json_output=json_output,
        )
    )


@evidence_derived_app.command("validate")
def evidence_derived_validate(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Validate all recorded derived evidence (formula safety, operands, cycles, staleness)."""
    from paperforge.commands.evidence_cmd import run_validate

    raise typer.Exit(
        code=run_validate(project_root=path.resolve(), kind="derived", json_output=json_output)
    )


@evidence_statistical_app.command("add")
def evidence_statistical_add(
    evidence_id: str = typer.Option(..., "--id", help="Unique evidence id."),
    test_name: str | None = typer.Option(None, "--test-name"),
    statistic: float | None = typer.Option(None, "--statistic"),
    p_value: float | None = typer.Option(None, "--p-value"),
    adjusted_p_value: float | None = typer.Option(None, "--adjusted-p-value"),
    correction_family: str | None = typer.Option(
        None, "--correction-family", help="none, bonferroni, or holm."
    ),
    effect_size_name: str | None = typer.Option(None, "--effect-size-name"),
    effect_size_value: float | None = typer.Option(None, "--effect-size-value"),
    sample_size: int | None = typer.Option(None, "--sample-size"),
    paired: bool = typer.Option(False, "--paired/--not-paired"),
    alpha: float | None = typer.Option(None, "--alpha"),
    confidence_interval: str | None = typer.Option(
        None, "--confidence-interval", help="Comma-separated 'low,high'."
    ),
    groups: str | None = typer.Option(None, "--groups", help="Comma-separated group names."),
    observation_refs: str | None = typer.Option(
        None, "--observation-refs", help="Comma-separated direct-evidence ids these observations came from."
    ),
    notes: str | None = typer.Option(None, "--notes"),
    from_yaml: Path | None = typer.Option(
        None, "--from-yaml", help="Path to a YAML file with the full field set."
    ),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Record an explicit statistical result. Never runs a test automatically."""
    from paperforge.commands.evidence_cmd import run_statistical_add

    fields: dict[str, object] = {
        "test_name": test_name,
        "statistic": statistic,
        "p_value": p_value,
        "adjusted_p_value": adjusted_p_value,
        "correction_family": correction_family,
        "effect_size_name": effect_size_name,
        "effect_size_value": effect_size_value,
        "sample_size": sample_size,
        "paired": paired,
        "alpha": alpha,
        "notes": notes,
    }
    if confidence_interval:
        fields["confidence_interval"] = [
            float(x.strip()) for x in confidence_interval.split(",") if x.strip()
        ]
    if groups:
        fields["groups"] = [g.strip() for g in groups.split(",") if g.strip()]
    if observation_refs:
        fields["observation_refs"] = [
            o.strip() for o in observation_refs.split(",") if o.strip()
        ]
    raise typer.Exit(
        code=run_statistical_add(
            project_root=path.resolve(),
            evidence_id=evidence_id,
            from_yaml=from_yaml,
            fields=fields,
            json_output=json_output,
        )
    )


@evidence_statistical_app.command("validate")
def evidence_statistical_validate(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Validate all recorded statistical evidence."""
    from paperforge.commands.evidence_cmd import run_validate

    raise typer.Exit(
        code=run_validate(project_root=path.resolve(), kind="statistical", json_output=json_output)
    )


@evidence_app.command("show")
def evidence_show(
    evidence_id: str | None = typer.Option(None, "--id", help="Show only this evidence id."),
    kind: str | None = typer.Option(
        None, "--kind", help="Filter to direct, derived, or statistical."
    ),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Show recorded evidence."""
    from paperforge.commands.evidence_cmd import run_show

    raise typer.Exit(
        code=run_show(
            project_root=path.resolve(), evidence_id=evidence_id, kind=kind, json_output=json_output
        )
    )


@evidence_app.command("graph")
def evidence_graph(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Show the evidence dependency graph: nodes, edges, cycles, missing refs, staleness."""
    from paperforge.commands.evidence_cmd import run_graph

    raise typer.Exit(code=run_graph(project_root=path.resolve(), json_output=json_output))


@evidence_app.command("validate")
def evidence_validate(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Validate the whole evidence store: records, cycles, missing refs, staleness."""
    from paperforge.commands.evidence_cmd import run_validate

    raise typer.Exit(
        code=run_validate(project_root=path.resolve(), kind=None, json_output=json_output)
    )


approvals_app = typer.Typer(
    name="approvals",
    help="Author-review approvals for generated provenance sentences, "
    "claims, and evidence records. Distinct from `paperforge review` "
    "(AI-assisted advisory review).",
)
app.add_typer(approvals_app, name="approvals")


@approvals_app.command("list")
def approvals_list(
    section: str | None = typer.Option(
        None, "--section", help="Filter to sentence ids in this section."
    ),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """List every reviewable object and its effective approval status."""
    from paperforge.commands.approvals_cmd import run_list

    raise typer.Exit(
        code=run_list(project_root=path.resolve(), section=section, json_output=json_output)
    )


def _approvals_decide_command(decision: str) -> Callable[..., None]:
    def handler(
        object_id: str | None = typer.Argument(
            None, help="Object id: evidence id, provenance sentence id (section:claim_id), or claim id."
        ),
        section: str | None = typer.Option(
            None, "--section", help="Apply to every generated sentence in this section."
        ),
        reviewer: str | None = typer.Option(
            None, "--reviewer", help="Reviewer identity. Defaults to git user.name, or 'agent' with --non-interactive."
        ),
        note: str = typer.Option("", "--note", help="Optional review note."),
        non_interactive: bool = typer.Option(
            False, "--non-interactive", help="Record reviewer as 'agent' if --reviewer is not given."
        ),
        path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
        json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
    ) -> None:
        from paperforge.commands.approvals_cmd import run_decide

        raise typer.Exit(
            code=run_decide(
                project_root=path.resolve(),
                object_id=object_id,
                section=section,
                decision=decision,
                reviewer=reviewer,
                note=note,
                non_interactive=non_interactive,
                json_output=json_output,
            )
        )

    handler.__doc__ = {
        "approved": "Approve a generated sentence, claim, or evidence record.",
        "rejected": "Reject a generated sentence, claim, or evidence record.",
        "pending": "Reset a reviewed object back to pending.",
    }[decision]
    return handler


approvals_app.command("approve")(_approvals_decide_command("approved"))
approvals_app.command("reject")(_approvals_decide_command("rejected"))
approvals_app.command("reset")(_approvals_decide_command("pending"))


outputs_app = typer.Typer(
    name="outputs", help="Inspect build output artifacts (current/previous)."
)
app.add_typer(outputs_app, name="outputs")


@outputs_app.command("list")
def outputs_list(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """List current/previous build outputs and any staging directories."""
    from paperforge.commands.outputs_cmd import run_list

    raise typer.Exit(
        code=run_list(project_root=path.resolve(), json_output=json_output)
    )


@outputs_app.command("verify")
def outputs_verify(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    target: str = typer.Option("current", "--target", help="current or previous."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Verify build-output artifact completeness (files present, non-trivial size, valid PDF header)."""
    from paperforge.commands.outputs_cmd import run_verify

    raise typer.Exit(
        code=run_verify(
            project_root=path.resolve(), target=target, json_output=json_output
        )
    )


@app.command()
def promote(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Verify the current build output and record it as the promoted submission candidate."""
    from paperforge.commands.outputs_cmd import run_promote

    raise typer.Exit(
        code=run_promote(project_root=path.resolve(), json_output=json_output)
    )


@app.command()
def rollback(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Atomically swap current and previous build outputs. Resumes an interrupted rollback safely."""
    from paperforge.commands.outputs_cmd import run_rollback

    raise typer.Exit(
        code=run_rollback(project_root=path.resolve(), json_output=json_output)
    )


@app.command()
def capture(
    results: Path = typer.Argument(..., help="Path to metrics JSON file."),
    experiment: str = typer.Option(
        ..., "--experiment", "-e", help="Experiment ID, e.g. exp_27"
    ),
    path: Path = typer.Option(
        Path("."), "--path", "-p", help="Project root. Defaults to current directory."
    ),
) -> None:
    """Capture experiment results and create a draft claim."""
    from paperforge.commands.capture import run

    run(
        results=results.resolve(), experiment_id=experiment, project_root=path.resolve()
    )


@app.command()
def doctor(
    path: Path = typer.Option(
        Path("."), "--path", "-p", help="Project root. Defaults to current directory."
    ),
    fix: bool = typer.Option(False, "--fix", help="Auto-resolve fixable warnings."),
    target: str | None = typer.Option(
        None,
        "--target",
        "-t",
        help="Venue target for additional checks: ieee, acm, neurips",
    ),
    self_check: bool = typer.Option(
        False, "--self-check", help="Check PaperForge installation health."
    ),
    pre_submission: bool = typer.Option(
        False, "--pre-submission", help="Run full submission readiness report."
    ),
    fix_hints: bool = typer.Option(
        False, "--fix-hints", help="Show concrete fix suggestions for each issue."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output issues as JSON for tooling integration."
    ),
) -> None:
    """Check research project consistency."""
    from paperforge.commands.doctor import run

    run(
        project_root=path.resolve(),
        fix=fix,
        target=target,
        self_check=self_check,
        pre_submission=pre_submission,
        fix_hints=fix_hints,
        json_output=json_output,
    )


@app.command()
def impact(
    experiment_id: str = typer.Argument(..., help="Experiment ID, e.g. exp_27"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
) -> None:
    """Show everything affected by a change to an experiment."""
    from paperforge.commands.impact import run

    run(experiment_id=experiment_id, project_root=path.resolve())


@app.command()
def build(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    target: str = typer.Option(
        "ieee", "--target", "-t", help="Venue target: ieee, acm, neurips"
    ),
    no_reveal: bool = typer.Option(
        False, "--no-reveal", help="Do not open output folder after build."
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force rebuild even if PDF is up to date."
    ),
    force_anyway: bool = typer.Option(
        False,
        "--force-anyway",
        help="Build even if doctor checks fail. NOT recommended for submission.",
    ),
    mode: str = typer.Option(
        "draft",
        "--mode",
        "-m",
        help="Build mode: draft or submission. Submission mode blocks on all P0 failures.",
    ),
) -> None:
    """Compile research data into an IEEE LaTeX paper."""
    from paperforge.commands.build import run

    run(
        project_root=path.resolve(),
        target=target,
        no_reveal=no_reveal,
        force=force,
        force_anyway=force_anyway,
        mode=mode,
    )


@app.command()
def review(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="llm model to use, e.g. gpt-4o. Uses llm default if omitted.",
    ),
) -> None:
    """AI-assisted paper review. Advisory only."""
    from paperforge.commands.review import run

    run(project_root=path.resolve(), model=model)


@app.command()
def improve(
    claim_id: str | None = typer.Argument(
        None,
        help="Specific claim ID to improve, e.g. claim_01",
    ),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="llm model to use. Uses llm default if omitted.",
    ),
    all_claims: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Improve all unverified claims.",
    ),
) -> None:
    """AI-assisted claim improvement. Suggests edits, never auto-applies."""
    from paperforge.commands.improve import run

    run(
        project_root=path.resolve(),
        claim_id=claim_id,
        model=model,
        all_claims=all_claims,
    )


@app.command(name="add-claim")
def add_claim(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    text: str | None = typer.Option(
        None, "--text", "-t", help="Claim text (non-interactive)"
    ),
    experiment: str | None = typer.Option(
        None, "--experiment", "-e", help="Experiment ID"
    ),
    sections: str | None = typer.Option(
        None,
        "--sections",
        "-s",
        help="Comma-separated section list, e.g. results,abstract",
    ),
    figures: str | None = typer.Option(
        None, "--figures", help="Comma-separated figure IDs, e.g. fig_01,fig_02"
    ),
    tables: str | None = typer.Option(
        None, "--tables", help="Comma-separated table IDs, e.g. tbl_01"
    ),
    citations: str | None = typer.Option(
        None,
        "--citations",
        "-c",
        help="Comma-separated BibTeX keys, e.g. smith2024,jones2023",
    ),
    status: str | None = typer.Option(
        None, "--status", help="Claim status: verified, unverified, stale"
    ),
    from_yaml: Path | None = typer.Option(
        None, "--from-yaml", help="Path to YAML file to import claim from"
    ),
) -> None:
    """Interactively create or script a new claim linked to an experiment."""
    from paperforge.commands.add_claim import run

    run(
        project_root=path.resolve(),
        text=text,
        experiment=experiment,
        sections=sections,
        figures=figures,
        tables=tables,
        citations=citations,
        status=status,
        from_yaml=from_yaml,
    )


@app.command(name="add-figure")
def add_figure(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    caption: str | None = typer.Option(None, "--caption", help="Figure caption"),
    fig_path: str | None = typer.Option(
        None, "--path-file", help="Relative path to image file, e.g. figures/fig_01.png"
    ),
    format: str | None = typer.Option(
        None, "--format", help="Image format: png, pdf, eps, svg"
    ),
    width: float | None = typer.Option(
        None, "--width", help="Intended LaTeX width in inches, e.g. 3.5"
    ),
    dpi: int | None = typer.Option(None, "--dpi", help="Resolution DPI, e.g. 300"),
    section: str | None = typer.Option(
        None, "--section", help="First mentioned in section"
    ),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes"),
    wide: bool = typer.Option(
        False, "--wide", help="Spans both columns in IEEE layout"
    ),
    from_yaml: Path | None = typer.Option(
        None, "--from-yaml", help="Path to YAML file to import figure from"
    ),
) -> None:
    """Interactively create or script a new figure YAML file."""
    from paperforge.commands.add_figure import run

    run(
        project_root=path.resolve(),
        caption=caption,
        path=fig_path,
        format=format,
        width=width,
        dpi=dpi,
        section=section,
        notes=notes,
        wide=wide,
        from_yaml=from_yaml,
    )


@app.command(name="generate-figures")
def generate_figures(
    figure_id: str | None = typer.Argument(
        None, help="Specific figure ID, or all if omitted"
    ),
    path: Path = typer.Option(Path("."), "--path", "-p"),
) -> None:
    """Generate matplotlib figures from experiment data."""
    from paperforge.commands.generate_figures import run

    run(project_root=path.resolve(), figure_id=figure_id)


@app.command(name="add-table")
def add_table(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    caption: str | None = typer.Option(None, "--caption", help="Table caption"),
    experiment: str | None = typer.Option(
        None, "--experiment", "-e", help="Source experiment ID"
    ),
    columns: str | None = typer.Option(
        None, "--columns", help="Comma-separated column headers"
    ),
    section: str | None = typer.Option(
        None, "--section", help="First mentioned in section"
    ),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes"),
    wide: bool = typer.Option(
        False, "--wide", help="Spans both columns in IEEE layout"
    ),
    from_yaml: Path | None = typer.Option(
        None, "--from-yaml", help="Path to YAML file to import table from"
    ),
) -> None:
    """Interactively create or script a new table YAML file."""
    from paperforge.commands.add_table import run

    run(
        project_root=path.resolve(),
        caption=caption,
        experiment=experiment,
        columns=columns,
        section=section,
        notes=notes,
        wide=wide,
        from_yaml=from_yaml,
    )


@app.command(name="add-citation")
def add_citation(
    key: str | None = typer.Argument(
        None,
        help="BibTeX key, e.g. smith2024. Prompted if omitted.",
    ),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    type_str: str | None = typer.Option(
        None, "--type", help="Citation type: article, inproceedings, book, etc."
    ),
    authors: str | None = typer.Option(
        None,
        "--authors",
        help="Semicolon-separated author list, e.g. Smith, A.; Jones, B.",
    ),
    title: str | None = typer.Option(None, "--title", help="Publication title"),
    year: int | None = typer.Option(None, "--year", help="Publication year"),
    venue: str | None = typer.Option(None, "--venue", help="Venue or journal name"),
    volume: str | None = typer.Option(None, "--volume", help="Volume number"),
    number: str | None = typer.Option(None, "--number", help="Issue or number"),
    pages: str | None = typer.Option(None, "--pages", help="Page range, e.g. 123--135"),
    doi: str | None = typer.Option(
        None, "--doi", help="DOI without https://doi.org/ prefix"
    ),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes"),
    from_yaml: Path | None = typer.Option(
        None, "--from-yaml", help="Path to YAML file to import citation from"
    ),
) -> None:
    """Interactively add or script citation metadata for a BibTeX key."""
    from paperforge.commands.add_citation import run

    run(
        project_root=path.resolve(),
        key=key,
        type_str=type_str,
        authors=authors,
        title=title,
        year=year,
        venue=venue,
        volume=volume,
        number=number,
        pages=pages,
        doi=doi,
        notes=notes,
        from_yaml=from_yaml,
    )


@app.command(name="import")
def import_content(
    section: str | None = typer.Argument(
        None, help="Section to import, e.g. 'abstract'. All if omitted."
    ),
    path: Path = typer.Option(Path("."), "--path", "-p"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing claims with same text."
    ),
) -> None:
    """Import content from paper_information/ into .paperforge/."""
    from paperforge.commands.import_content import run

    run(project_root=path.resolve(), section=section, force=force)


@app.command(name="install-hooks")
def install_hooks(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    uninstall: bool = typer.Option(False, "--uninstall", help="Remove the hook."),
) -> None:
    """Install a git pre-commit hook that runs paperforge doctor."""
    from paperforge.commands.install_hooks import run

    run(project_root=path.resolve(), uninstall=uninstall)


@app.command()
def export(
    fmt: str = typer.Argument(
        "json", help="Format: bibtex, json, markdown, traceability, overleaf"
    ),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path or directory. Defaults to .paperforge/output/.",
    ),
) -> None:
    """Export research graph as BibTeX, JSON, Markdown, Traceability Matrix, or Overleaf zip."""
    from paperforge.commands.export import run

    run(
        project_root=path.resolve(),
        fmt=fmt,
        output=output.resolve() if output else None,
    )


@app.command()
def status(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
) -> None:
    """Show project health dashboard."""
    from paperforge.commands.status import run

    run(project_root=path.resolve())


@app.command()
def find(
    query: str = typer.Argument(..., help="Search term."),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    field: str = typer.Option(
        "all",
        "--field",
        "-f",
        help="Search scope: claims, experiments, all",
    ),
) -> None:
    """Search claims and experiments by keyword."""
    from paperforge.commands.find import run

    run(query=query, project_root=path.resolve(), field=field)


@app.command(name="log")
def log_cmd(
    claim_id: str = typer.Argument(..., help="Claim ID, e.g. claim_01"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    limit: int = typer.Option(
        10, "--limit", "-n", help="Maximum number of history entries to show."
    ),
) -> None:
    """Show change history for a claim."""
    from paperforge.commands.log_cmd import run

    run(claim_id=claim_id, project_root=path.resolve(), limit=limit)


@app.command()
def diff(
    claim_id: str = typer.Argument(..., help="Claim ID, e.g. claim_01"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    against: str = typer.Option(
        "previous",
        "--against",
        "-a",
        help="Diff target: previous, HEAD~1, experiment",
    ),
) -> None:
    """Show what changed in a claim vs its history or linked experiment."""
    from paperforge.commands.diff import run

    run(claim_id=claim_id, project_root=path.resolve(), against=against)


@app.command()
def venues() -> None:
    """List available venue targets for --target option."""
    from rich.console import Console
    from rich.table import Table

    from paperforge.venues.registry import get_plugin, list_plugins

    console = Console()
    table = Table(title="Available Venue Targets")
    table.add_column("Target", style="cyan")
    table.add_column("Display Name")
    table.add_column("Document Class")
    table.add_column("Page Limit")
    for name in list_plugins():
        plugin = get_plugin(name)
        table.add_row(
            plugin.name,
            plugin.display_name,
            plugin.latex_documentclass[:40] + "...",
            str(plugin.max_pages) if plugin.max_pages else "None",
        )
    console.print(table)


venue_app = typer.Typer(
    name="venue",
    help="Versioned per-venue metadata (adapter version, source, checked "
    "date). Distinct from `paperforge venues` (lists targets).",
)
app.add_typer(venue_app, name="venue")


@venue_app.command("show")
def venue_show(
    target: str | None = typer.Option(
        None, "--target", "-t", help="Built-in venue id, e.g. ieee, acm, neurips."
    ),
    custom_file: str | None = typer.Option(
        None, "--custom-file", help="Project-relative path to a custom venue YAML file."
    ),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Show a venue's versioned metadata: adapter version, source, checked date."""
    from paperforge.commands.venue_cmd import run_show

    raise typer.Exit(
        code=run_show(
            project_root=path.resolve(), target=target, custom_file=custom_file, json_output=json_output
        )
    )


@venue_app.command("validate")
def venue_validate(
    target: str | None = typer.Option(None, "--target", "-t"),
    custom_file: str | None = typer.Option(None, "--custom-file"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Validate a venue's metadata (built-in or a custom local file)."""
    from paperforge.commands.venue_cmd import run_validate

    raise typer.Exit(
        code=run_validate(
            project_root=path.resolve(), target=target, custom_file=custom_file, json_output=json_output
        )
    )


@app.command()
def update(
    pre: bool = typer.Option(False, "--pre", help="Include pre-release versions."),
    git: bool = typer.Option(
        False, "--git", help="Update from git (for development installs)."
    ),
) -> None:
    """Update paperforge-research to the latest version."""
    from paperforge.commands.update import run

    run(pre=pre, git=git)


@app.command()
def sync(
    direction: str = typer.Option(
        "status",
        "--direction",
        "-d",
        help="Sync direction: to-md, to-claims, or status",
    ),
    path: Path = typer.Option(Path("."), "--path", "-p"),
    force: bool = typer.Option(False, "--force", "-f"),
) -> None:
    """Sync between paper_information/ and .paperforge/ (bidirectional)."""
    from paperforge.commands.sync import run

    run(project_root=path.resolve(), direction=direction, force=force)


@app.command()
def validate(
    path: Path = typer.Option(Path("."), "--path", "-p"),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output path for VALIDATION_LOG.md"
    ),
) -> None:
    """Validate all numerical claims against experiment data."""
    from paperforge.commands.validate import run

    run(project_root=path.resolve(), output=output)


@app.command()
def clean(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
) -> None:
    """Remove stale build artifacts and LaTeX aux files."""
    from paperforge.commands.clean import run

    run(project_root=path.resolve())


@app.command()
def preflight(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    mode: str = typer.Option(
        "draft", "--mode", "-m", help="Build mode: draft or submission."
    ),
    pdf: Path | None = typer.Option(None, "--pdf", help="Custom PDF path to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
    open_renders: bool = typer.Option(
        False, "--open-renders", help="Open rendered page images folder."
    ),
) -> None:
    """Run rendered PDF preflight, template fingerprinting, visual overlap & structural checks."""
    from paperforge.commands.preflight import run

    run(
        project_root=path.resolve(),
        mode=mode,
        pdf_path=pdf,
        json_output=json_output,
        open_renders=open_renders,
    )


@app.command()
def references(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project root."),
    online: bool = typer.Option(
        False, "--online", help="Verify DOIs against Crossref API."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Verify BibTeX reference metadata and optionally check DOIs against Crossref."""
    from paperforge.core.project import PaperForgeProject
    from paperforge.services.reference_verifier import verify_references
    from paperforge.utils.envelope import (
        EXIT_REFERENCES_ERROR,
        EXIT_SUCCESS,
        ResultEnvelope,
        print_envelope,
    )

    project_root = path.resolve()
    project = PaperForgeProject.load(project_root)
    reports_dir = (
        project.output_dir.parent.parent / "reports"
        if project.output_dir.parent.name == "paper_generated"
        else project.output_dir / "reports"
    )
    reports_dir.mkdir(parents=True, exist_ok=True)

    rep = verify_references(project, reports_dir, online=online)

    if json_output:
        env = ResultEnvelope(command="references", project_root=str(project_root))
        env.outputs["report"] = rep.to_dict()
        if not rep.passed:
            for issue in rep.issues:
                env.errors.append(
                    {
                        "code": str(issue.get("code", "REFERENCE_ISSUE")),
                        "field_path": str(issue.get("citation_key", "")),
                        "message": str(issue.get("message", issue)),
                        "remediation": str(issue.get("remediation", "")),
                        "severity": str(issue.get("severity", "ERROR")),
                        "line": None,
                        "column": None,
                    }
                )
        env.finalize(EXIT_REFERENCES_ERROR)
        if not env.errors:
            env.status, env.exit_code = "success", EXIT_SUCCESS
        raise typer.Exit(code=print_envelope(env))

    typer.echo(
        f"Reference verification complete. Checked {rep.total_citations} references "
        f"(online verified: {rep.online_verified_count}). Status: {'PASSED' if rep.passed else 'ISSUES FOUND'}"
    )


if __name__ == "__main__":
    app()
