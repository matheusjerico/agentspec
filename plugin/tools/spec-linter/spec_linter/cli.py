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
names the consumer context, it never reinterprets a verdict.

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
    every additional piece (`execution.final_review`, `report_contract`) it needs."""
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

    return BuildReportContract(
        required_sections=required,
        verdicts=verdicts,
        fix_budget=fix_budget,
        schema_version=schema_version,
        tdd_mode_values=tdd_mode_values,
        legacy_level=legacy_level,
    )


def _lint_phase(path: Path, phase: str, contracts_file: Path, legacy_mode: str) -> Level:
    """Lint a Markdown phase document against its phase contract."""
    data = _load_contracts_data(contracts_file)
    contract: Contract
    if phase == "build":
        contract = _build_report_contract(data, contracts_file, legacy_mode)
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
