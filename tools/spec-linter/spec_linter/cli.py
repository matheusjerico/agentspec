"""CLI: `python -m spec_linter.cli [path] [--phase NAME] [--emit-schema OUT.json]`.

Lints a spec file or a directory of specs against the baked-in agent-spec
contract, or (with `--phase`) a Markdown phase document against an
`SddPhaseContract`. The CLI is a consumer of the engine and owns the usage
policy: YAML/Markdown loading, directory iteration, the cross-file duplicate-id
(L4) check, and contract selection.

`--phase build` is a special case: it loads the full `build` block of the
contracts YAML (`required_sections`, `execution.final_review`,
`report_contract`) and runs a `BuildReportContract` instead of
`SddPhaseContract`, layering semantic `BR.*` rules on top of section
presence. `--legacy-mode {warn,fail}` (default `warn`) selects which
contract-declared severity — `report_contract.legacy.manual` or `.autopilot`
— applies to a pre-contract (schema-version-less) report; the flag only
names the consumer context, it never reinterprets a verdict. When the
contracts data also carries a top-level `tdd_policy` mapping, its
`risk_policy` and `exception_categories` are passed to the contract too,
enabling `BR.tdd_required_by_risk`/`BR.tdd_exception_invalid`; absent or
non-mapping `tdd_policy` leaves both rules off — silent, backward compatible.
The top-level `task_review` block follows the identical opt-in shape:
`verdicts` supplies `BR.task_review_missing`/`BR.task_review_dirty`; absent
or non-mapping `task_review` leaves both off.

`--phase define` is similarly conditional: when the loaded contracts data
carries a top-level `risk_profiles` mapping, it runs a `DefinePhaseContract`
instead, layering WARN-only `RP.*` risk-profile rules on top of the phase's
existing `L2.required_section` (FAIL) checks; malformed `risk_profiles`
subkeys are an operational ERROR (exit 2), never a verdict. When
`risk_profiles` is absent from the contracts data, `--phase define` falls
back silently to the plain `SddPhaseContract` path — backward compatible
with contracts files that predate the risk-profile rollout.

`--phase design` follows the same conditional shape: when the loaded
contracts data carries a top-level `task_manifest` mapping, a top-level
`traceability` mapping, or both, it runs a `DesignPhaseContract` instead,
layering FAIL-level `TM.*` executable-manifest rules (opt-in per DESIGN
document — absent v2 block is v1-silent, zero `TM.*` findings) and/or
FAIL/WARN `TX.*` traceability-matrix rules (Increment 6, opt-in per DESIGN
document the same way) on top of `L2.required_section`; malformed
`task_manifest`/`traceability` subkeys are an operational ERROR (exit 2).
When only one of the two blocks is present, the other's rule family stays
structurally silent (`TM.*` via empty vocabularies, `TX.*` via
`verification_types=None`). Absent BOTH `task_manifest` and `traceability`
falls back silently to `SddPhaseContract`, identical to the
define/risk_profiles pattern.

Exit codes form a three-way contract:

- 0 — PASS or WARN verdict.
- 1 — FAIL verdict (a loadable artifact that violates its contract).
- 2 — ERROR: an operational failure (file not found, YAML syntax error, a
  non-mapping top level, an unknown phase, or any unexpected exception). ERROR
  is a process concern only — it is NOT a Verdict Level; the Verdict surface
  stays exactly PASS/WARN/FAIL.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from . import rules
from .contracts.agent_spec import AgentSpecContract, emit_json_schema
from .contracts.build_report import BuildReportContract
from .contracts.define_phase import DefinePhaseContract
from .contracts.design_phase import DesignPhaseContract
from .contracts.sdd_phase import SddPhaseContract
from .engine import lint
from .protocol import Contract
from .verdict import Level, Verdict

_CONTRACT = AgentSpecContract()

# Tool-root-relative default; the CLI lives at tools/spec-linter/spec_linter/cli.py.
def _resolve_default_contracts_file(tool_root: Path) -> Path:
    """Probe both layouts and return the first that exists.

    A repo checkout nests the file under `.claude/`; the installed plugin does
    not (its root already is the former `.claude/`). Falls back to the repo
    layout so a genuinely missing file still degrades loudly (exit 2) with an
    informative path instead of silently picking a nonexistent default.
    """
    repo_layout = tool_root / ".claude" / "sdd" / "architecture" / "WORKFLOW_CONTRACTS.yaml"
    plugin_layout = tool_root / "sdd" / "architecture" / "WORKFLOW_CONTRACTS.yaml"
    return next((p for p in (repo_layout, plugin_layout) if p.exists()), repo_layout)


_DEFAULT_CONTRACTS_FILE = _resolve_default_contracts_file(Path(__file__).resolve().parents[3])


class _OperationalError(Exception):
    """Raised for failures that must map to exit code 2 (ERROR), not a verdict."""


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: expected a YAML mapping at the top level")
    return data


def _lint_file(path: Path) -> Verdict:
    """Lint one YAML spec file against the agent-spec contract."""
    return lint(_load_yaml(path), _CONTRACT)


def _lint_dir(path: Path) -> dict[str, Verdict]:
    """Lint every `.yaml`/`.yml` file in a directory, keyed by file name.

    Adds the cross-file duplicate-id (L4) check on top of the per-file
    verdicts: a duplicated id appends the same finding to every file that
    claims it.
    """
    files = sorted(p for p in path.iterdir() if p.suffix in (".yaml", ".yml"))
    verdicts: dict[str, Verdict] = {}
    ids_by_source: dict[str, list[str]] = {}
    for file in files:
        data = _load_yaml(file)
        verdicts[file.name] = lint(data, _CONTRACT)
        spec_id = data.get("id")
        if isinstance(spec_id, str):
            ids_by_source.setdefault(spec_id, []).append(file.name)
    for spec_id, sources in ids_by_source.items():
        for finding in rules.l4_identity_findings({spec_id: sources}):
            for source in sources:
                verdicts[source] = Verdict.from_findings([*verdicts[source].findings, finding])
    return verdicts


def _load_contracts_data(contracts_file: Path) -> dict[str, Any]:
    """Load a WORKFLOW_CONTRACTS-style YAML file's top-level mapping."""
    if not contracts_file.exists():
        raise _OperationalError(f"contracts file not found: {contracts_file}")
    try:
        data = yaml.safe_load(contracts_file.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise _OperationalError(f"could not parse contracts file {contracts_file}: {exc}") from exc
    return data or {}


def _phase_required_sections(phase: str, data: dict[str, Any], contracts_file: Path) -> list[str]:
    """Read a phase's `required_sections` from already-loaded contracts data."""
    block = data.get(phase)
    if not isinstance(block, dict) or "required_sections" not in block:
        raise _OperationalError(
            f"phase '{phase}' has no required_sections in {contracts_file.name}"
        )
    sections = block["required_sections"]
    if not isinstance(sections, list) or not all(isinstance(s, str) for s in sections):
        raise _OperationalError(f"phase '{phase}' required_sections must be a list of strings")
    return sections


def _build_report_contract(
    data: dict[str, Any], contracts_file: Path, legacy_mode: str
) -> BuildReportContract:
    """Assemble the build-phase contract from the `build` block of already-loaded
    contracts data, mirroring `_phase_required_sections`'s validation style for
    every additional piece (`execution.final_review`, `report_contract`) it needs.

    The top-level `tdd_policy` block is optional: a dict supplies
    `risk_policy`/`exception_categories` to the contract; anything else
    (absent, non-dict) passes `None`/`None`, leaving the two `BR.tdd_*` risk
    rules off. The top-level `task_review` block is optional the same way: a
    dict supplies `verdicts`, arming `BR.task_review_missing`/
    `BR.task_review_dirty`; anything else passes `None`, leaving both off.
    The top-level `traceability` block (Increment 6) is optional the same
    way: a dict arms `matrix_must_coverage=True`, enabling `BR.must_uncovered`/
    `BR.matrix_missing`; anything else leaves both off. Unlike `tdd_policy`/
    `task_review`, no subkey validation is needed here — the build side only
    needs the boolean "is traceability configured", not a vocabulary."""
    required = _phase_required_sections("build", data, contracts_file)
    block = data["build"]

    execution = block.get("execution")
    final_review = execution.get("final_review") if isinstance(execution, dict) else None
    if not isinstance(final_review, dict):
        raise _OperationalError(
            f"phase 'build' has no execution.final_review in {contracts_file.name}"
        )
    verdicts = final_review.get("verdicts")
    if not isinstance(verdicts, list) or not all(isinstance(v, str) for v in verdicts):
        raise _OperationalError(
            f"phase 'build' execution.final_review.verdicts must be a list of strings "
            f"in {contracts_file.name}"
        )
    fix_budget = final_review.get("fix_loop_budget")
    if not isinstance(fix_budget, int):
        raise _OperationalError(
            f"phase 'build' execution.final_review.fix_loop_budget must be an int "
            f"in {contracts_file.name}"
        )

    report_contract = block.get("report_contract")
    if not isinstance(report_contract, dict):
        raise _OperationalError(f"phase 'build' has no report_contract in {contracts_file.name}")
    schema_version = report_contract.get("schema_version")
    if not isinstance(schema_version, int):
        raise _OperationalError(
            f"phase 'build' report_contract.schema_version must be an int in {contracts_file.name}"
        )
    tdd_mode_values = report_contract.get("tdd_mode_values")
    if not isinstance(tdd_mode_values, list) or not all(
        isinstance(v, str) for v in tdd_mode_values
    ):
        raise _OperationalError(
            f"phase 'build' report_contract.tdd_mode_values must be a list of strings "
            f"in {contracts_file.name}"
        )
    legacy = report_contract.get("legacy")
    if not isinstance(legacy, dict) or "manual" not in legacy or "autopilot" not in legacy:
        raise _OperationalError(
            f"phase 'build' report_contract.legacy must define manual and autopilot "
            f"in {contracts_file.name}"
        )
    legacy_key = "autopilot" if legacy_mode == "fail" else "manual"
    try:
        legacy_level = Level[legacy[legacy_key]]
    except (KeyError, TypeError) as exc:
        raise _OperationalError(
            f"phase 'build' report_contract.legacy.{legacy_key} is not a valid severity "
            f"level in {contracts_file.name}"
        ) from exc

    risk_tdd_policy: dict[str, str] | None = None
    tdd_exception_categories: list[str] | None = None
    tdd_policy = data.get("tdd_policy")
    if isinstance(tdd_policy, dict):
        risk_policy = tdd_policy.get("risk_policy")
        if not isinstance(risk_policy, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in risk_policy.items()
        ):
            raise _OperationalError(
                f"tdd_policy.risk_policy must be a mapping of strings to strings "
                f"in {contracts_file.name}"
            )
        exception_categories = tdd_policy.get("exception_categories")
        if not isinstance(exception_categories, list) or not all(
            isinstance(v, str) for v in exception_categories
        ):
            raise _OperationalError(
                f"tdd_policy.exception_categories must be a list of strings "
                f"in {contracts_file.name}"
            )
        # Closed vocabulary: a typo'd obligation ("Required", "requried") would
        # otherwise fail OPEN — silently disabling the TDD floor for that level.
        allowed_obligations = {"recommended", "required_for_logic", "required"}
        unknown = sorted(set(risk_policy.values()) - allowed_obligations)
        if unknown:
            raise _OperationalError(
                f"tdd_policy.risk_policy values must be one of "
                f"{sorted(allowed_obligations)}; got {unknown} in {contracts_file.name}"
            )
        risk_tdd_policy = risk_policy
        tdd_exception_categories = exception_categories

    task_review_verdicts: list[str] | None = None
    task_review = data.get("task_review")
    if isinstance(task_review, dict):
        review_verdicts = task_review.get("verdicts")
        if not isinstance(review_verdicts, list) or not all(
            isinstance(v, str) for v in review_verdicts
        ):
            raise _OperationalError(
                f"task_review.verdicts must be a list of strings in {contracts_file.name}"
            )
        task_review_verdicts = review_verdicts

    matrix_must_coverage = isinstance(data.get("traceability"), dict)

    metrics_config: dict[str, Any] | None = None
    workflow_metrics = data.get("workflow_metrics")
    if isinstance(workflow_metrics, dict):
        metrics_schema_version = workflow_metrics.get("schema_version")
        if not isinstance(metrics_schema_version, int):
            raise _OperationalError(
                f"workflow_metrics.schema_version must be an int in {contracts_file.name}"
            )
        catalog = workflow_metrics.get("catalog")
        if (
            not isinstance(catalog, list)
            or not catalog
            or not all(isinstance(k, str) for k in catalog)
        ):
            raise _OperationalError(
                f"workflow_metrics.catalog must be a non-empty list of strings "
                f"in {contracts_file.name}"
            )
        metrics_config = {"schema_version": metrics_schema_version, "catalog": catalog}

    return BuildReportContract(
        required_sections=required,
        verdicts=verdicts,
        fix_budget=fix_budget,
        schema_version=schema_version,
        tdd_mode_values=tdd_mode_values,
        legacy_level=legacy_level,
        risk_tdd_policy=risk_tdd_policy,
        tdd_exception_categories=tdd_exception_categories,
        task_review_verdicts=task_review_verdicts,
        matrix_must_coverage=matrix_must_coverage,
        metrics_config=metrics_config,
    )


def _define_phase_contract(data: dict[str, Any], contracts_file: Path) -> DefinePhaseContract:
    """Assemble the define-phase contract from `define.required_sections` plus
    the top-level `risk_profiles` block of already-loaded contracts data,
    mirroring `_build_report_contract`'s validation style for every piece it
    needs."""
    required = _phase_required_sections("define", data, contracts_file)
    block = data["risk_profiles"]

    levels = block.get("levels")
    if not isinstance(levels, list) or not all(isinstance(v, str) for v in levels):
        raise _OperationalError(
            f"risk_profiles.levels must be a list of strings in {contracts_file.name}"
        )
    dimensions = block.get("dimensions")
    if not isinstance(dimensions, list) or not all(isinstance(v, str) for v in dimensions):
        raise _OperationalError(
            f"risk_profiles.dimensions must be a list of strings in {contracts_file.name}"
        )
    dimension_values = block.get("dimension_values")
    if not isinstance(dimension_values, list) or not all(
        isinstance(v, str) for v in dimension_values
    ):
        raise _OperationalError(
            f"risk_profiles.dimension_values must be a list of strings in {contracts_file.name}"
        )

    override = block.get("override")
    override_required = override.get("required_fields") if isinstance(override, dict) else None
    if not isinstance(override_required, list) or not all(
        isinstance(v, str) for v in override_required
    ):
        raise _OperationalError(
            f"risk_profiles.override.required_fields must be a list of strings "
            f"in {contracts_file.name}"
        )

    legacy = block.get("legacy")
    legacy_level = legacy.get("effective_level") if isinstance(legacy, dict) else None
    if not isinstance(legacy_level, str):
        raise _OperationalError(
            f"risk_profiles.legacy.effective_level must be a string in {contracts_file.name}"
        )
    if legacy_level not in levels:
        raise _OperationalError(
            f"risk_profiles.legacy.effective_level '{legacy_level}' is not one of "
            f"risk_profiles.levels in {contracts_file.name}"
        )
    if [v for v in dimension_values if v in set(levels)] != levels:
        raise _OperationalError(
            "risk_profiles.levels must appear in risk_profiles.dimension_values in the "
            f"same order (rank comparability) in {contracts_file.name}"
        )

    return DefinePhaseContract(
        required_sections=required,
        levels=levels,
        dimensions=dimensions,
        dimension_values=dimension_values,
        override_required=override_required,
        legacy_level=legacy_level,
    )


def _design_phase_contract(data: dict[str, Any], contracts_file: Path) -> DesignPhaseContract:
    """Assemble the design-phase contract from `design.required_sections` plus
    the top-level `task_manifest` and `traceability` blocks of already-loaded
    contracts data, mirroring `_define_phase_contract`'s validation style for
    every piece it needs.

    The two top-level blocks are independently optional and independently
    arm their rule families — the caller's routing gate only requires at
    least one to be present. A dict `task_manifest` supplies the `TM.*`
    vocabularies (`required_task_fields`/`files_keys`/`verification_keys`);
    when it's absent, empty-list defaults keep `TM.*` structurally silent (a
    v1 DESIGN with no manifest section never reaches `_check_manifest`
    regardless). A dict `traceability` supplies `verification_types`, arming
    `TX.*`; when it's absent, `verification_types=None` leaves `TX.*` off —
    identical posture to every other opt-in family in this CLI."""
    required = _phase_required_sections("design", data, contracts_file)
    block = data.get("task_manifest")

    if isinstance(block, dict):
        required_task_fields = block.get("required_task_fields")
        if not isinstance(required_task_fields, list) or not all(
            isinstance(v, str) for v in required_task_fields
        ):
            raise _OperationalError(
                f"task_manifest.required_task_fields must be a list of strings in {contracts_file.name}"
            )
        files_keys = block.get("files_keys")
        if not isinstance(files_keys, list) or not all(isinstance(v, str) for v in files_keys):
            raise _OperationalError(
                f"task_manifest.files_keys must be a list of strings in {contracts_file.name}"
            )
        verification_keys = block.get("verification_keys")
        if not isinstance(verification_keys, list) or not all(
            isinstance(v, str) for v in verification_keys
        ):
            raise _OperationalError(
                f"task_manifest.verification_keys must be a list of strings in {contracts_file.name}"
            )
    else:
        required_task_fields, files_keys, verification_keys = [], [], []

    verification_types: list[str] | None = None
    traceability = data.get("traceability")
    if isinstance(traceability, dict):
        types = traceability.get("verification_types")
        if not isinstance(types, list) or not all(isinstance(v, str) for v in types):
            raise _OperationalError(
                f"traceability.verification_types must be a list of strings in {contracts_file.name}"
            )
        verification_types = types

    return DesignPhaseContract(
        required_sections=required,
        required_task_fields=required_task_fields,
        files_keys=files_keys,
        verification_keys=verification_keys,
        verification_types=verification_types,
        manifest_configured=isinstance(block, dict),
    )


def _lint_phase(path: Path, phase: str, contracts_file: Path, legacy_mode: str) -> Level:
    """Lint a Markdown phase document against its phase contract."""
    data = _load_contracts_data(contracts_file)
    contract: Contract
    if phase == "build":
        contract = _build_report_contract(data, contracts_file, legacy_mode)
    elif phase == "define" and isinstance(data.get("risk_profiles"), dict):
        contract = _define_phase_contract(data, contracts_file)
    elif phase == "design" and (
        isinstance(data.get("task_manifest"), dict) or isinstance(data.get("traceability"), dict)
    ):
        contract = _design_phase_contract(data, contracts_file)
    else:
        required = _phase_required_sections(phase, data, contracts_file)
        contract = SddPhaseContract(phase, required)
    verdict = lint(path.read_text(encoding="utf-8"), contract)
    print(f"== {path.name} (phase: {phase}) ==")
    print(verdict)
    return verdict.level


def _write_schema(out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(emit_json_schema(), indent=2) + "\n")
    print(f"Wrote JSON Schema to {out}")


def _lint_path(path: Path) -> Level:
    if path.is_dir():
        verdicts = _lint_dir(path)
        worst = Level.PASS
        for name, verdict in verdicts.items():
            print(f"== {name} ==")
            print(verdict)
            print()
            worst = max(worst, verdict.level)
        print(f"OVERALL: {worst.name}")
        return worst

    verdict = _lint_file(path)
    print(f"== {path.name} ==")
    print(verdict)
    return verdict.level


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spec_linter", description="AgentSpec contract-validation engine (the Linter)."
    )
    parser.add_argument("path", nargs="?", help="spec file/dir, or phase document with --phase")
    parser.add_argument(
        "--phase",
        metavar="NAME",
        help="lint PATH as a Markdown phase document against the named phase contract",
    )
    parser.add_argument(
        "--contracts-file",
        metavar="PATH",
        type=Path,
        default=_DEFAULT_CONTRACTS_FILE,
        help="WORKFLOW_CONTRACTS-style YAML source for --phase required_sections",
    )
    parser.add_argument(
        "--legacy-mode",
        choices=("warn", "fail"),
        default="warn",
        help=(
            "only affects `--phase build` on a legacy (pre-contract) report: which "
            "contract-declared severity (report_contract.legacy.manual/.autopilot) "
            "applies — names the consumer context (manual vs. autopilot), never "
            "reinterprets a verdict"
        ),
    )
    parser.add_argument(
        "--emit-schema",
        metavar="OUT.json",
        type=Path,
        help="write the spec JSON Schema to OUT.json",
    )
    args = parser.parse_args(argv)

    if args.emit_schema is not None:
        _write_schema(args.emit_schema)
        if args.path is None:
            return 0

    if args.path is None:
        parser.error("a path is required unless only --emit-schema is given")

    try:
        if args.phase is not None:
            level = _lint_phase(Path(args.path), args.phase, args.contracts_file, args.legacy_mode)
        else:
            level = _lint_path(Path(args.path))
    except FileNotFoundError as exc:
        print(f"ERROR: file not found: {exc.filename or args.path}", file=sys.stderr)
        return 2
    except (yaml.YAMLError, ValueError, _OperationalError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # operational failure, not a verdict
        print(f"ERROR: unexpected failure: {exc}", file=sys.stderr)
        return 2

    return 1 if level == Level.FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
