"""Implementation behind `paperforge evidence ...`.

Every subcommand builds a :class:`ResultEnvelope` and follows the same
exit-code conventions as `manifest`/`plan`/`generate` (see
`paperforge.utils.envelope`). Non-JSON output is a short human summary.
"""

from __future__ import annotations

import json as json_module
from pathlib import Path
from typing import Any

from paperforge.evidence import formula as formula_mod
from paperforge.evidence import sources
from paperforge.evidence.graph import (
    compute_staleness,
    detect_cycles,
    find_missing_references,
    recompute_dependency_hash_for,
)
from paperforge.evidence.models import (
    DerivedEvidence,
    DirectEvidence,
    StatisticalEvidence,
    apply_precision,
    sha256_text,
)
from paperforge.evidence.store import EvidenceStore, load_store, save_store
from paperforge.evidence.validators import (
    validate_derived_formula,
    validate_direct,
    validate_statistical,
    validate_store,
)
from paperforge.project_manifest.path_safety import check_project_path
from paperforge.utils.envelope import (
    EXIT_CLI_MISUSE,
    EXIT_EVIDENCE_ERROR,
    EXIT_SUCCESS,
    ResultEnvelope,
    print_envelope,
)


def _echo(env: ResultEnvelope, json_output: bool, lines: list[str]) -> int:
    if json_output:
        return print_envelope(env)
    import typer

    for line in lines:
        typer.echo(line)
    return env.exit_code


def _fail(
    env: ResultEnvelope,
    code: str,
    message: str,
    json_output: bool,
    *,
    exit_code: int = EXIT_EVIDENCE_ERROR,
) -> int:
    env.errors.append(
        {
            "code": code,
            "field_path": "",
            "message": message,
            "remediation": "",
            "severity": "ERROR",
            "line": None,
            "column": None,
        }
    )
    env.finalize(exit_code)
    return _echo(env, json_output, [f"error: {message}"])


def run_direct_add(
    *,
    project_root: Path,
    evidence_id: str,
    source_type: str,
    source_path: str,
    source_locator: str,
    value: str | None,
    value_type: str,
    unit: str,
    sample_size: int | None,
    observations_count: int | None,
    notes: str,
    json_output: bool,
) -> int:
    env = ResultEnvelope(command="evidence direct add", project_root=str(project_root))

    if not evidence_id:
        return _fail(
            env,
            "EVIDENCE_MISSING_ID",
            "--id is required.",
            json_output,
            exit_code=EXIT_CLI_MISUSE,
        )

    store = load_store(project_root)
    if evidence_id in store.all_ids():
        return _fail(
            env,
            "EVIDENCE_DUPLICATE_ID",
            f"Evidence id '{evidence_id}' already exists. Use a new id (evidence records are immutable by id).",
            json_output,
        )

    if source_type == "manual":
        if value is None:
            return _fail(
                env,
                "EVIDENCE_MISSING_VALUE",
                "--value is required for type=manual.",
                json_output,
                exit_code=EXIT_CLI_MISUSE,
            )
        parsed_value = _parse_manual_value(value, value_type)
        content_hash = sha256_text(f"{evidence_id}:{value_type}:{value}")
        resolved_source_path = ""
    else:
        if source_type not in {"csv", "json", "yaml"}:
            return _fail(
                env,
                "EVIDENCE_INVALID_TYPE",
                f"type must be one of csv, json, yaml, manual (got '{source_type}').",
                json_output,
                exit_code=EXIT_CLI_MISUSE,
            )
        check = check_project_path(
            project_root, source_path, field_path="evidence.direct.source_path"
        )
        if not check.ok or check.resolved is None:
            return _fail(env, check.code or "PATH_INVALID", check.reason, json_output)
        try:
            parsed_value, content_hash = sources.extract(
                source_type, check.resolved, source_locator
            )
        except sources.SourceExtractionError as exc:
            return _fail(
                env, "EVIDENCE_SOURCE_EXTRACTION_FAILED", str(exc), json_output
            )
        resolved_source_path = source_path
        if value_type == "number" and not isinstance(parsed_value, int | float):
            try:
                parsed_value = float(parsed_value)
            except (TypeError, ValueError):
                pass

    ev = DirectEvidence(
        id=evidence_id,
        type=source_type,
        source_path=resolved_source_path,
        source_locator=source_locator,
        content_hash=content_hash,
        value=parsed_value,
        value_type=value_type,
        unit=unit,
        sample_size=sample_size,
        observations_count=observations_count,
        notes=notes,
    )

    issues = validate_direct(ev)
    errors = [i for i in issues if i["severity"] == "ERROR"]
    if errors:
        for i in errors:
            env.errors.append(
                {
                    "code": i["code"],
                    "field_path": "",
                    "message": i["message"],
                    "remediation": i.get("remediation", ""),
                    "severity": "ERROR",
                    "line": None,
                    "column": None,
                }
            )
        env.finalize(EXIT_EVIDENCE_ERROR)
        return _echo(env, json_output, [f"error: {e['message']}" for e in env.errors])

    store.direct[evidence_id] = ev
    save_store(project_root, store)

    env.outputs["evidence"] = ev.to_dict()
    env.finalize(EXIT_EVIDENCE_ERROR)
    return _echo(
        env,
        json_output,
        [f"Recorded direct evidence '{evidence_id}' = {parsed_value} {unit}".rstrip()],
    )


def _parse_manual_value(raw: str, value_type: str) -> Any:
    if value_type == "number":
        try:
            return int(raw)
        except ValueError:
            return float(raw)
    if value_type == "bool":
        return raw.strip().lower() in {"true", "1", "yes"}
    return raw


def run_derived_add(
    *,
    project_root: Path,
    evidence_id: str,
    formula: str,
    operand_ids: list[str],
    unit: str,
    precision: int | None,
    rounding: str,
    notes: str,
    json_output: bool,
) -> int:
    env = ResultEnvelope(command="evidence derived add", project_root=str(project_root))

    if not evidence_id:
        return _fail(
            env,
            "EVIDENCE_MISSING_ID",
            "--id is required.",
            json_output,
            exit_code=EXIT_CLI_MISUSE,
        )

    store = load_store(project_root)
    if evidence_id in store.all_ids():
        return _fail(
            env,
            "EVIDENCE_DUPLICATE_ID",
            f"Evidence id '{evidence_id}' already exists.",
            json_output,
        )

    candidate = DerivedEvidence(
        id=evidence_id,
        formula=formula,
        operand_ids=operand_ids,
        unit=unit,
        precision=precision,
        rounding=rounding,
        notes=notes,
    )

    trial_store = EvidenceStore(
        dict(store.direct),
        {**store.derived, evidence_id: candidate},
        dict(store.statistical),
    )
    issues = validate_derived_formula(candidate, trial_store)
    errors = [i for i in issues if i["severity"] == "ERROR"]
    if errors:
        for i in errors:
            env.errors.append(
                {
                    "code": i["code"],
                    "field_path": "",
                    "message": i["message"],
                    "remediation": i.get("remediation", ""),
                    "severity": "ERROR",
                    "line": None,
                    "column": None,
                }
            )
        env.finalize(EXIT_EVIDENCE_ERROR)
        return _echo(env, json_output, [f"error: {e['message']}" for e in env.errors])

    cycles = detect_cycles(trial_store)
    if cycles.has_cycles:
        return _fail(
            env,
            "EVIDENCE_DEPENDENCY_CYCLE",
            f"Adding '{evidence_id}' would create a cycle: {cycles.cycles[0]}.",
            json_output,
        )

    operand_values: dict[str, float] = {}
    for op in operand_ids:
        if op in store.direct:
            try:
                operand_values[op] = store.direct[op].numeric_value()
            except ValueError as exc:
                return _fail(env, "EVIDENCE_NON_NUMERIC_OPERAND", str(exc), json_output)
        elif op in store.derived:
            if store.derived[op].result is None:
                return _fail(
                    env,
                    "EVIDENCE_OPERAND_HAS_NO_RESULT",
                    f"Operand '{op}' has not been evaluated yet.",
                    json_output,
                )
            operand_values[op] = store.derived[op].result  # type: ignore[assignment]
        else:
            return _fail(
                env,
                "EVIDENCE_MISSING_OPERAND",
                f"Operand '{op}' does not exist in the evidence store.",
                json_output,
            )

    try:
        result = formula_mod.evaluate(formula, operand_values)
    except formula_mod.FormulaSecurityError as exc:
        return _fail(env, "EVIDENCE_UNSAFE_FORMULA", str(exc), json_output)
    except formula_mod.FormulaEvaluationError as exc:
        return _fail(env, "EVIDENCE_FORMULA_EVALUATION_ERROR", str(exc), json_output)

    final_value = apply_precision(result.value, precision, rounding)
    candidate.result = final_value
    candidate.dependency_hash = recompute_dependency_hash_for(trial_store, candidate)

    store.derived[evidence_id] = candidate
    save_store(project_root, store)

    env.outputs["evidence"] = candidate.to_dict()
    env.finalize(EXIT_EVIDENCE_ERROR)
    return _echo(
        env,
        json_output,
        [f"Recorded derived evidence '{evidence_id}' = {final_value} {unit}".rstrip()],
    )


def run_statistical_add(
    *,
    project_root: Path,
    evidence_id: str,
    from_yaml: Path | None,
    fields: dict[str, Any],
    json_output: bool,
) -> int:
    env = ResultEnvelope(
        command="evidence statistical add", project_root=str(project_root)
    )

    if not evidence_id:
        return _fail(
            env,
            "EVIDENCE_MISSING_ID",
            "--id is required.",
            json_output,
            exit_code=EXIT_CLI_MISUSE,
        )

    store = load_store(project_root)
    if evidence_id in store.all_ids():
        return _fail(
            env,
            "EVIDENCE_DUPLICATE_ID",
            f"Evidence id '{evidence_id}' already exists.",
            json_output,
        )

    data: dict[str, Any] = {}
    if from_yaml is not None:
        import yaml

        yaml_file = from_yaml if from_yaml.is_absolute() else project_root / from_yaml
        if not yaml_file.exists():
            return _fail(
                env,
                "EVIDENCE_YAML_NOT_FOUND",
                f"--from-yaml file not found: {from_yaml}",
                json_output,
                exit_code=EXIT_CLI_MISUSE,
            )
        loaded = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            data.update(loaded)
    data.update({k: v for k, v in fields.items() if v is not None})
    data["id"] = evidence_id

    ev = StatisticalEvidence.from_dict(data)

    issues = validate_statistical(ev)
    errors = [i for i in issues if i["severity"] == "ERROR"]
    if errors:
        for i in errors:
            env.errors.append(
                {
                    "code": i["code"],
                    "field_path": "",
                    "message": i["message"],
                    "remediation": i.get("remediation", ""),
                    "severity": "ERROR",
                    "line": None,
                    "column": None,
                }
            )
        env.finalize(EXIT_EVIDENCE_ERROR)
        return _echo(env, json_output, [f"error: {e['message']}" for e in env.errors])

    for ref in ev.observation_refs:
        if ref not in store.all_ids():
            return _fail(
                env,
                "EVIDENCE_MISSING_OPERAND",
                f"observation_refs references unknown evidence '{ref}'.",
                json_output,
            )
    if ev.observation_refs:
        payload = {
            "refs": sorted(ev.observation_refs),
            "hashes": {
                r: (
                    store.direct[r].content_hash
                    if r in store.direct
                    else store.derived[r].dependency_hash
                )
                for r in ev.observation_refs
            },
        }
        ev.dependency_hash = sha256_text(json_module.dumps(payload, sort_keys=True))

    store.statistical[evidence_id] = ev
    save_store(project_root, store)

    env.outputs["evidence"] = ev.to_dict()
    env.finalize(EXIT_EVIDENCE_ERROR)
    return _echo(
        env,
        json_output,
        [f"Recorded statistical evidence '{evidence_id}' ({ev.test_name})."],
    )


def run_show(
    *, project_root: Path, evidence_id: str | None, kind: str | None, json_output: bool
) -> int:
    env = ResultEnvelope(command="evidence show", project_root=str(project_root))
    store = load_store(project_root)

    records: dict[str, list[dict[str, Any]]] = {
        "direct": [],
        "derived": [],
        "statistical": [],
    }
    for eid, direct_ev in sorted(store.direct.items()):
        if (kind and kind != "direct") or (evidence_id and evidence_id != eid):
            continue
        records["direct"].append(direct_ev.to_dict())
    for eid, derived_ev in sorted(store.derived.items()):
        if (kind and kind != "derived") or (evidence_id and evidence_id != eid):
            continue
        records["derived"].append(derived_ev.to_dict())
    for eid, stat_ev in sorted(store.statistical.items()):
        if (kind and kind != "statistical") or (evidence_id and evidence_id != eid):
            continue
        records["statistical"].append(stat_ev.to_dict())

    total = sum(len(v) for v in records.values())
    if evidence_id and total == 0:
        env.warnings.append(
            {
                "code": "EVIDENCE_NOT_FOUND",
                "field_path": "",
                "message": f"No evidence with id '{evidence_id}'.",
                "remediation": "",
                "severity": "WARNING",
                "line": None,
                "column": None,
            }
        )

    env.outputs["evidence"] = records
    env.outputs["total"] = total
    env.finalize(EXIT_EVIDENCE_ERROR)
    if not env.errors:
        env.status = "success" if not env.warnings else "warning"
        env.exit_code = EXIT_SUCCESS

    lines = [
        f"Evidence: {len(records['direct'])} direct, {len(records['derived'])} derived, {len(records['statistical'])} statistical."
    ]
    for kind_name, items in records.items():
        for item in items:
            summary = item.get("value", item.get("result", item.get("test_name", "")))
            lines.append(f"  [{kind_name}] {item['id']} = {summary}")
    return _echo(env, json_output, lines)


def run_graph(*, project_root: Path, json_output: bool) -> int:
    env = ResultEnvelope(command="evidence graph", project_root=str(project_root))
    store = load_store(project_root)

    nodes = []
    for eid in sorted(store.direct):
        nodes.append({"id": eid, "kind": "direct"})
    for eid in sorted(store.derived):
        nodes.append({"id": eid, "kind": "derived"})
    for eid in sorted(store.statistical):
        nodes.append({"id": eid, "kind": "statistical"})

    edges = []
    for d in store.derived.values():
        for op in d.operand_ids:
            edges.append({"from": op, "to": d.id, "relation": "operand_of"})
    for s in store.statistical.values():
        for ref in s.observation_refs:
            edges.append({"from": ref, "to": s.id, "relation": "observation_of"})

    cycles = detect_cycles(store)
    missing = find_missing_references(store)
    staleness = (
        compute_staleness(project_root, store) if not cycles.has_cycles else None
    )

    env.outputs["nodes"] = nodes
    env.outputs["edges"] = edges
    env.outputs["cycles"] = cycles.cycles
    env.outputs["missing_references"] = [
        {
            "referencing_id": m.referencing_id,
            "referencing_kind": m.referencing_kind,
            "missing_id": m.missing_id,
        }
        for m in missing
    ]
    if staleness is not None:
        env.outputs["stale"] = sorted(staleness.stale_ids)
    else:
        env.outputs["stale"] = []
        env.warnings.append(
            {
                "code": "EVIDENCE_GRAPH_HAS_CYCLES",
                "field_path": "",
                "message": "Staleness cannot be computed while the graph has cycles.",
                "remediation": "Resolve the reported cycle(s) first.",
                "severity": "WARNING",
                "line": None,
                "column": None,
            }
        )

    if cycles.has_cycles or missing:
        for cycle in cycles.cycles:
            env.errors.append(
                {
                    "code": "EVIDENCE_DEPENDENCY_CYCLE",
                    "field_path": "",
                    "message": f"Cycle: {' -> '.join(cycle)}",
                    "remediation": "",
                    "severity": "ERROR",
                    "line": None,
                    "column": None,
                }
            )
        for m in missing:
            env.errors.append(
                {
                    "code": "EVIDENCE_MISSING_REFERENCE",
                    "field_path": "",
                    "message": f"'{m.referencing_id}' references unknown '{m.missing_id}'.",
                    "remediation": "",
                    "severity": "ERROR",
                    "line": None,
                    "column": None,
                }
            )
    env.finalize(EXIT_EVIDENCE_ERROR)
    if not env.errors:
        env.status = "success" if not env.warnings else "warning"
        env.exit_code = EXIT_SUCCESS

    lines = [
        f"Evidence graph: {len(nodes)} nodes, {len(edges)} edges, {len(cycles.cycles)} cycles, {len(missing)} missing references."
    ]
    return _echo(env, json_output, lines)


def run_validate(*, project_root: Path, kind: str | None, json_output: bool) -> int:
    env = ResultEnvelope(command="evidence validate", project_root=str(project_root))
    store = load_store(project_root)
    issues = validate_store(project_root, store)
    if kind:
        prefix = {
            "direct": "direct",
            "derived": "derived",
            "statistical": "statistical",
        }.get(kind)
        if prefix:
            issues = [
                i
                for i in issues
                if (kind == "direct" and i["evidence_id"] in store.direct)
                or (kind == "derived" and i["evidence_id"] in store.derived)
                or (kind == "statistical" and i["evidence_id"] in store.statistical)
                or i["evidence_id"] == ""
            ]

    for i in issues:
        entry = {
            "code": i["code"],
            "field_path": i.get("evidence_id", ""),
            "message": i["message"],
            "remediation": i.get("remediation", ""),
            "severity": i["severity"],
            "line": None,
            "column": None,
        }
        if i["severity"] == "ERROR":
            env.errors.append(entry)
        else:
            env.warnings.append(entry)

    env.outputs["total_records"] = (
        len(store.direct) + len(store.derived) + len(store.statistical)
    )
    env.outputs["issues"] = issues
    env.finalize(EXIT_EVIDENCE_ERROR)
    if not env.errors:
        env.status = "success" if not env.warnings else "warning"
        env.exit_code = EXIT_SUCCESS

    lines = [
        f"Evidence validation: {len(store.direct)} direct, {len(store.derived)} derived, {len(store.statistical)} statistical -- {len(env.errors)} errors, {len(env.warnings)} warnings."
    ]
    for e in env.errors:
        lines.append(f"  [ERROR] {e['code']} ({e['field_path']}): {e['message']}")
    return _echo(env, json_output, lines)


__all__ = [
    "run_derived_add",
    "run_direct_add",
    "run_graph",
    "run_show",
    "run_statistical_add",
    "run_validate",
]
