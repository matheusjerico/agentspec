"""Tests for the CLI: file/dir linting, exit codes, and JSON Schema emission."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from spec_linter import cli
from spec_linter.verdict import Level


def _write_spec(path: Path, spec: dict[str, Any]) -> Path:
    path.write_text(yaml.safe_dump(spec))
    return path


def test_valid_file_passes_with_exit_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], valid_spec: dict[str, Any]
) -> None:
    spec_file = _write_spec(tmp_path / "agent.yaml", valid_spec)
    assert cli.main([str(spec_file)]) == 0
    assert "VERDICT: PASS" in capsys.readouterr().out


def test_failing_file_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], valid_spec: dict[str, Any]
) -> None:
    valid_spec["observability"] = None
    spec_file = _write_spec(tmp_path / "agent.yaml", valid_spec)
    assert cli.main([str(spec_file)]) == 1
    out = capsys.readouterr().out
    assert "VERDICT: FAIL" in out
    assert "L2.maturity_observability" in out


def test_dir_lint_reports_overall_and_exits_one_on_any_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], valid_spec: dict[str, Any]
) -> None:
    _write_spec(tmp_path / "good.yaml", valid_spec)
    failing = {**valid_spec, "id": "another-agent", "publish": True, "security_review": False}
    _write_spec(tmp_path / "bad.yaml", failing)
    assert cli.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "== good.yaml ==" in out
    assert "== bad.yaml ==" in out
    assert "OVERALL: FAIL" in out


def test_duplicate_id_across_dir_is_fail(tmp_path: Path, valid_spec: dict[str, Any]) -> None:
    _write_spec(tmp_path / "a.yaml", valid_spec)
    _write_spec(tmp_path / "b.yaml", valid_spec)  # same id in both files

    verdicts = cli._lint_dir(tmp_path)
    assert set(verdicts) == {"a.yaml", "b.yaml"}
    for name in ("a.yaml", "b.yaml"):
        assert verdicts[name].level == Level.FAIL
        dupes = [f for f in verdicts[name].findings if f.rule == "L4.duplicate_id"]
        assert len(dupes) == 1
        assert "a.yaml" in dupes[0].found and "b.yaml" in dupes[0].found


def test_emit_schema_writes_file_creating_parent_dirs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out_path = tmp_path / "nested" / "agent_spec.schema.json"
    assert cli.main(["--emit-schema", str(out_path)]) == 0
    schema = json.loads(out_path.read_text())
    assert "output_contract" in schema["properties"]
    assert f"Wrote JSON Schema to {out_path}" in capsys.readouterr().out


def test_missing_file_is_error_exit_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "does_not_exist.yaml"
    assert cli.main([str(missing)]) == 2
    assert "ERROR:" in capsys.readouterr().err


def test_malformed_yaml_is_error_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "broken.yaml"
    bad.write_text("id: [unterminated\n")
    assert cli.main([str(bad)]) == 2
    assert "ERROR:" in capsys.readouterr().err


def test_non_mapping_yaml_is_error_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scalar = tmp_path / "scalar.yaml"
    scalar.write_text("just a string\n")
    assert cli.main([str(scalar)]) == 2
    assert "ERROR:" in capsys.readouterr().err


def test_error_exit_two_is_distinct_from_fail_exit_one(
    tmp_path: Path, valid_spec: dict[str, Any]
) -> None:
    valid_spec["observability"] = None  # loadable mapping, contract FAIL -> exit 1
    fail_file = _write_spec(tmp_path / "fail.yaml", valid_spec)
    assert cli.main([str(fail_file)]) == 1
    assert cli.main([str(tmp_path / "nope.yaml")]) == 2  # operational ERROR -> exit 2


def _write_phase_doc(path: Path, headings: list[str]) -> Path:
    path.write_text("\n\n".join(f"## {h}" for h in headings) + "\n")
    return path


def test_phase_doc_passes_with_exit_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(
        yaml.safe_dump({"define": {"required_sections": ["Problem Statement", "Goals"]}})
    )
    doc = _write_phase_doc(tmp_path / "DEFINE_X.md", ["Problem Statement", "Goals"])
    code = cli.main([str(doc), "--phase", "define", "--contracts-file", str(contracts)])
    assert code == 0
    assert "VERDICT: PASS" in capsys.readouterr().out


def test_phase_doc_missing_section_fails_with_exit_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(
        yaml.safe_dump({"define": {"required_sections": ["Problem Statement", "Goals"]}})
    )
    doc = _write_phase_doc(tmp_path / "DEFINE_X.md", ["Problem Statement"])
    code = cli.main([str(doc), "--phase", "define", "--contracts-file", str(contracts)])
    assert code == 1
    out = capsys.readouterr().out
    assert "VERDICT: FAIL" in out
    assert "L2.required_section" in out


def test_phase_unknown_phase_is_error_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump({"define": {"required_sections": ["Problem Statement"]}}))
    doc = _write_phase_doc(tmp_path / "DOC.md", ["Problem Statement"])
    code = cli.main([str(doc), "--phase", "nonexistent", "--contracts-file", str(contracts)])
    assert code == 2
    assert "ERROR:" in capsys.readouterr().err


def test_default_contracts_file_prefers_repo_layout(tmp_path: Path) -> None:
    repo_file = tmp_path / ".claude" / "sdd" / "architecture" / "WORKFLOW_CONTRACTS.yaml"
    repo_file.parent.mkdir(parents=True)
    repo_file.write_text("{}")
    assert cli._resolve_default_contracts_file(tmp_path) == repo_file


def test_default_contracts_file_falls_back_to_plugin_layout(tmp_path: Path) -> None:
    # No .claude/ prefix — this is the installed-plugin layout (the fixed bug).
    plugin_file = tmp_path / "sdd" / "architecture" / "WORKFLOW_CONTRACTS.yaml"
    plugin_file.parent.mkdir(parents=True)
    plugin_file.write_text("{}")
    assert cli._resolve_default_contracts_file(tmp_path) == plugin_file


# --- --phase build (BuildReportContract) ------------------------------------


def _build_contracts_data() -> dict[str, Any]:
    return {
        "build": {
            "required_sections": [
                "metadata",
                "summary",
                "task_execution_with_agent_attribution",
                "files_created",
                "verification_results",
                "review_verdict",
                "acceptance_test_verification",
                "final_status",
            ],
            "execution": {
                "final_review": {
                    "verdicts": ["clean", "clean-with-minors", "dirty", "missing"],
                    "fix_loop_budget": 2,
                }
            },
            "report_contract": {
                "schema_version": 2,
                "tdd_mode_values": ["off", "opt-in", "required"],
                "legacy": {"manual": "WARN", "autopilot": "FAIL"},
            },
        }
    }


def _write_build_contracts(path: Path) -> Path:
    path.write_text(yaml.safe_dump(_build_contracts_data()))
    return path


def _write_report(path: Path, text: str) -> Path:
    path.write_text(text)
    return path


_VALID_BUILD_REPORT = """\
# BUILD REPORT: CLI_SAMPLE

## Metadata

| Field | Value |
|-------|-------|
| **Schema Version** | 2 |
| **TDD Mode** | off |

## Summary

CLI-level fixture for build-phase contract tests.

## Task Execution with Agent Attribution

| # | Task | Agent | Status |
|---|------|-------|--------|
| 1 | Implement feature | python-pro | ✅ |

## Files Created

- `src/cli_sample.py`

## Verification Results

- `pytest tests/` - 1 passed

## Review Verdict

| Field | Value |
|-------|-------|
| **Verdict** | clean |
| **Fix rounds used** | 0/2 |

## Acceptance Test Verification

| Acceptance Test | Status |
|------------------|--------|
| Sample behaves correctly | ✅ Verified |

## Final Status

### Overall: ✅ COMPLETE
"""


def test_build_phase_valid_v2_report_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_build_contracts(tmp_path / "contracts.yaml")
    report = _write_report(tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", _VALID_BUILD_REPORT)
    code = cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)])
    assert code == 0
    assert "VERDICT: PASS" in capsys.readouterr().out


def test_build_phase_dirty_verdict_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_build_contracts(tmp_path / "contracts.yaml")
    dirty = _VALID_BUILD_REPORT.replace("| **Verdict** | clean |", "| **Verdict** | dirty |")
    report = _write_report(tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", dirty)
    code = cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)])
    assert code == 1
    out = capsys.readouterr().out
    assert "VERDICT: FAIL" in out
    assert "BR.review_verdict_dirty" in out


def test_build_phase_legacy_report_defaults_to_warn_exit_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_build_contracts(tmp_path / "contracts.yaml")
    legacy = _VALID_BUILD_REPORT.replace("| **Schema Version** | 2 |\n", "")
    report = _write_report(tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", legacy)
    code = cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)])
    assert code == 0
    out = capsys.readouterr().out
    assert "VERDICT: WARN" in out
    assert "BR.legacy_report" in out


def test_build_phase_legacy_report_with_legacy_mode_fail_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_build_contracts(tmp_path / "contracts.yaml")
    legacy = _VALID_BUILD_REPORT.replace("| **Schema Version** | 2 |\n", "")
    report = _write_report(tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", legacy)
    code = cli.main(
        [
            str(report),
            "--phase",
            "build",
            "--contracts-file",
            str(contracts),
            "--legacy-mode",
            "fail",
        ]
    )
    assert code == 1
    out = capsys.readouterr().out
    assert "VERDICT: FAIL" in out
    assert "BR.legacy_report" in out


def test_build_phase_invalid_legacy_mode_is_argparse_error(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(
            [
                str(tmp_path / "irrelevant.md"),
                "--phase",
                "build",
                "--legacy-mode",
                "banana",
            ]
        )
    assert exc_info.value.code == 2


def test_build_phase_missing_report_contract_block_is_error_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = _build_contracts_data()
    del data["build"]["report_contract"]
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(data))
    report = _write_report(tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", _VALID_BUILD_REPORT)
    code = cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)])
    assert code == 2
    assert "ERROR:" in capsys.readouterr().err


# --- --phase define (DefinePhaseContract) ------------------------------------


_DEFINE_REQUIRED_SECTIONS = [
    "metadata",
    "problem_statement",
    "target_users",
    "goals",
    "success_criteria",
    "acceptance_tests",
    "out_of_scope",
    "constraints",
    "assumptions",
    "clarity_score_breakdown",
    "open_questions",
    "revision_history",
]


def _define_contracts_data() -> dict[str, Any]:
    return {
        "define": {"required_sections": _DEFINE_REQUIRED_SECTIONS},
        "risk_profiles": {
            "rollout": "observe_warn",
            "levels": ["low", "medium", "high", "critical"],
            "dimensions": [
                "data_loss",
                "security",
                "reversibility",
                "blast_radius",
                "migration",
            ],
            "dimension_values": ["none", "low", "medium", "high", "critical"],
            "override": {"required_fields": ["author", "rationale"]},
            "legacy": {"effective_level": "medium", "mode": "WARN"},
        },
    }


def _write_define_contracts(path: Path) -> Path:
    path.write_text(yaml.safe_dump(_define_contracts_data()))
    return path


def _write_define_doc(path: Path, text: str) -> Path:
    path.write_text(text)
    return path


_VALID_DEFINE_DOC = """\
# DEFINE: CLI_SAMPLE

## Metadata

Feature metadata.

## Problem Statement

Sample problem statement.

## Target Users

Sample target users.

## Goals

- MUST support sample goal.

## Success Criteria

- Sample succeeds.

## Acceptance Tests

- Given/when/then.

## Out of Scope

- Not covered here.

## Constraints

- Sample constraint.

## Risk Profile

```yaml
risk_profile:
  level: medium
  dimensions:
    data_loss: medium
    security: medium
    reversibility: medium
    blast_radius: medium
    migration: medium
  override:
    applied: false
    author: null
    rationale: null
```

## Assumptions

- Sample assumption.

## Clarity Score Breakdown

- 15/15.

## Open Questions

- None.

## Revision History

- Initial draft.
"""


def _define_doc_without_profile() -> str:
    """`_VALID_DEFINE_DOC` with its `## Risk Profile` section removed —
    every required section still present, no Risk Profile block at all."""
    start = _VALID_DEFINE_DOC.index("## Risk Profile")
    end = _VALID_DEFINE_DOC.index("## Assumptions")
    return _VALID_DEFINE_DOC[:start] + _VALID_DEFINE_DOC[end:]


def test_define_phase_valid_doc_with_profile_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_define_contracts(tmp_path / "contracts.yaml")
    doc = _write_define_doc(tmp_path / "DEFINE_CLI_SAMPLE.md", _VALID_DEFINE_DOC)
    code = cli.main([str(doc), "--phase", "define", "--contracts-file", str(contracts)])
    assert code == 0
    assert "VERDICT: PASS" in capsys.readouterr().out


def test_define_phase_without_profile_warns_but_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_define_contracts(tmp_path / "contracts.yaml")
    doc = _write_define_doc(tmp_path / "DEFINE_CLI_SAMPLE.md", _define_doc_without_profile())
    code = cli.main([str(doc), "--phase", "define", "--contracts-file", str(contracts)])
    assert code == 0
    out = capsys.readouterr().out
    assert "VERDICT: WARN" in out
    assert "RP.profile_missing" in out


def test_define_phase_falls_back_to_plain_contract_without_risk_profiles_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = _define_contracts_data()
    del data["risk_profiles"]
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(data))
    doc = _write_define_doc(tmp_path / "DEFINE_CLI_SAMPLE.md", _define_doc_without_profile())
    code = cli.main([str(doc), "--phase", "define", "--contracts-file", str(contracts)])
    assert code == 0
    out = capsys.readouterr().out
    assert "RP." not in out


def test_define_phase_risk_profiles_missing_levels_is_error_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = _define_contracts_data()
    del data["risk_profiles"]["levels"]
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(data))
    doc = _write_define_doc(tmp_path / "DEFINE_CLI_SAMPLE.md", _VALID_DEFINE_DOC)
    code = cli.main([str(doc), "--phase", "define", "--contracts-file", str(contracts)])
    assert code == 2
    assert "ERROR:" in capsys.readouterr().err


def test_define_phase_missing_required_section_with_valid_profile_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_define_contracts(tmp_path / "contracts.yaml")
    start = _VALID_DEFINE_DOC.index("## Out of Scope")
    end = _VALID_DEFINE_DOC.index("## Constraints")
    missing_section_doc = _VALID_DEFINE_DOC[:start] + _VALID_DEFINE_DOC[end:]
    doc = _write_define_doc(tmp_path / "DEFINE_CLI_SAMPLE.md", missing_section_doc)
    code = cli.main([str(doc), "--phase", "define", "--contracts-file", str(contracts)])
    assert code == 1
    out = capsys.readouterr().out
    assert "VERDICT: FAIL" in out
    assert "L2.required_section" in out


def test_define_phase_levels_not_rank_comparable_is_error_exit_two(tmp_path, capsys):
    data = _define_contracts_data()
    data["risk_profiles"]["levels"] = ["critical", "high", "medium", "low"]
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(data))
    doc = tmp_path / "DEFINE_X.md"
    doc.write_text(_VALID_DEFINE_DOC)
    assert cli.main([str(doc), "--phase", "define", "--contracts-file", str(contracts)]) == 2


def test_define_phase_legacy_level_outside_levels_is_error_exit_two(tmp_path, capsys):
    data = _define_contracts_data()
    data["risk_profiles"]["legacy"]["effective_level"] = "meduim"
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(data))
    doc = tmp_path / "DEFINE_X.md"
    doc.write_text(_VALID_DEFINE_DOC)
    assert cli.main([str(doc), "--phase", "define", "--contracts-file", str(contracts)]) == 2


# --- --phase design (DesignPhaseContract) ------------------------------------


_DESIGN_REQUIRED_SECTIONS = [
    "architecture_overview",
    "components",
    "key_decisions",
    "file_manifest",
    "code_patterns",
    "testing_strategy",
]


def _design_contracts_data() -> dict[str, Any]:
    return {
        "design": {"required_sections": _DESIGN_REQUIRED_SECTIONS},
        "task_manifest": {
            "manifest_version": 2,
            "required_task_fields": ["id", "title", "files", "verification"],
            "files_keys": ["create", "modify", "tests"],
            "verification_keys": ["red", "green", "regression"],
        },
    }


def _write_design_contracts(path: Path) -> Path:
    path.write_text(yaml.safe_dump(_design_contracts_data()))
    return path


def _write_design_doc(path: Path, text: str) -> Path:
    path.write_text(text)
    return path


_VALID_DESIGN_DOC = """\
# DESIGN: CLI_SAMPLE

## Architecture Overview

Sample architecture overview.

## Components

Sample components.

## Key Decisions

Sample key decisions.

## File Manifest

Sample file manifest.

## Task Manifest (v2)

```yaml
task_manifest:
  manifest_version: 2
  tasks:
    - id: TASK-A
      title: Implement module A
      requirements: ["REQ-1"]
      depends_on: []
      files:
        create: ["fileA.py"]
        modify: []
        tests: ["test_fileA.py"]
      verification:
        green: "pytest tests/test_fileA.py"
    - id: TASK-B
      title: Implement module B
      requirements: ["REQ-2"]
      depends_on: ["TASK-A"]
      files:
        create: ["fileB.py"]
        modify: []
        tests: ["test_fileB.py"]
      verification:
        green: "pytest tests/test_fileB.py"
```

## Code Patterns

Sample code patterns.

## Testing Strategy

Sample testing strategy.
"""


def _design_doc_without_manifest() -> str:
    """`_VALID_DESIGN_DOC` with its `## Task Manifest (v2)` section removed —
    every required section still present, no v2 manifest block at all."""
    start = _VALID_DESIGN_DOC.index("## Task Manifest (v2)")
    end = _VALID_DESIGN_DOC.index("## Code Patterns")
    return _VALID_DESIGN_DOC[:start] + _VALID_DESIGN_DOC[end:]


def _design_doc_with_cycle() -> str:
    """`_VALID_DESIGN_DOC` with TASK-A also depending on TASK-B — a two-task
    dependency cycle."""
    return _VALID_DESIGN_DOC.replace(
        "      depends_on: []\n", '      depends_on: ["TASK-B"]\n'
    )


def test_design_phase_valid_v2_doc_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_design_contracts(tmp_path / "contracts.yaml")
    doc = _write_design_doc(tmp_path / "DESIGN_CLI_SAMPLE.md", _VALID_DESIGN_DOC)
    code = cli.main([str(doc), "--phase", "design", "--contracts-file", str(contracts)])
    assert code == 0
    assert "VERDICT: PASS" in capsys.readouterr().out


def test_design_phase_cycle_doc_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_design_contracts(tmp_path / "contracts.yaml")
    doc = _write_design_doc(tmp_path / "DESIGN_CLI_SAMPLE.md", _design_doc_with_cycle())
    code = cli.main([str(doc), "--phase", "design", "--contracts-file", str(contracts)])
    assert code == 1
    out = capsys.readouterr().out
    assert "VERDICT: FAIL" in out
    assert "TM.cycle" in out


def test_design_phase_without_manifest_section_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_design_contracts(tmp_path / "contracts.yaml")
    doc = _write_design_doc(tmp_path / "DESIGN_CLI_SAMPLE.md", _design_doc_without_manifest())
    code = cli.main([str(doc), "--phase", "design", "--contracts-file", str(contracts)])
    assert code == 0
    assert "VERDICT: PASS" in capsys.readouterr().out


def test_design_phase_falls_back_to_plain_contract_without_task_manifest_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = _design_contracts_data()
    del data["task_manifest"]
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(data))
    # Even a doc that WOULD cycle under a v2 manifest exits 0 here: without
    # the `task_manifest` key, `--phase design` falls back silently to the
    # plain `SddPhaseContract` — only required_sections are checked.
    doc = _write_design_doc(tmp_path / "DESIGN_CLI_SAMPLE.md", _design_doc_with_cycle())
    code = cli.main([str(doc), "--phase", "design", "--contracts-file", str(contracts)])
    assert code == 0
    out = capsys.readouterr().out
    assert "VERDICT: PASS" in out
    assert "TM." not in out


def test_design_phase_required_task_fields_not_a_list_is_error_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = _design_contracts_data()
    data["task_manifest"]["required_task_fields"] = "id"
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(data))
    doc = _write_design_doc(tmp_path / "DESIGN_CLI_SAMPLE.md", _VALID_DESIGN_DOC)
    code = cli.main([str(doc), "--phase", "design", "--contracts-file", str(contracts)])
    assert code == 2
    assert "ERROR:" in capsys.readouterr().err


# --- --phase build, tdd_policy (BR.tdd_required_by_risk) ---------------------


def _tdd_policy_block() -> dict[str, Any]:
    """The real top-level `tdd_policy` shape from WORKFLOW_CONTRACTS.yaml.
    The CLI only reads `risk_policy`/`exception_categories`; the rest is
    carried along because this mirrors the on-disk contract, not a
    CLI-specific shape."""
    return {
        "effective_mode_rule": (
            "strongest of: --tdd flag (opt-in), risk_policy[risk level], any "
            "manifest task with execution.tdd == required"
        ),
        "risk_policy": {
            "low": "recommended",
            "medium": "required_for_logic",
            "high": "required",
            "critical": "required",
        },
        "no_tdd_flag": {
            "dispenses": ["low", "medium"],
            "requires": "recorded_justification",
            "never": ["high", "critical"],
        },
        "exception_categories": [
            "non_executable_documentation",
            "declarative_configuration",
            "generated_artifact",
            "vendored_content",
            "infrastructure_declaration",
        ],
        "red_validity": (
            "a broken RED command, an unrelated import error, or a pre-existing "
            "failure is not RED evidence"
        ),
        "enforcement": {
            "high_critical_off": "FAIL",
            "medium_off": "WARN",
            "low_off": "silent",
            "no_risk_row": "silent",
        },
    }


def _build_contracts_data_with_tdd_policy() -> dict[str, Any]:
    data = _build_contracts_data()
    data["tdd_policy"] = _tdd_policy_block()
    return data


_VALID_BUILD_REPORT_HIGH_RISK_TDD_OFF = _VALID_BUILD_REPORT.replace(
    "| **TDD Mode** | off |\n",
    "| **TDD Mode** | off |\n| **Risk Level** | high |\n",
)


def test_build_phase_tdd_required_by_risk_high_off_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = _build_contracts_data_with_tdd_policy()
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(data))
    report = _write_report(
        tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", _VALID_BUILD_REPORT_HIGH_RISK_TDD_OFF
    )
    code = cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)])
    assert code == 1
    out = capsys.readouterr().out
    assert "VERDICT: FAIL" in out
    assert "BR.tdd_required_by_risk" in out


def test_build_phase_tdd_policy_absent_leaves_rule_off_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_build_contracts(tmp_path / "contracts.yaml")  # no tdd_policy key
    report = _write_report(
        tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", _VALID_BUILD_REPORT_HIGH_RISK_TDD_OFF
    )
    code = cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)])
    assert code == 0
    out = capsys.readouterr().out
    assert "VERDICT: PASS" in out
    assert "BR.tdd_required_by_risk" not in out


def test_build_phase_tdd_policy_risk_policy_not_a_dict_is_error_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = _build_contracts_data_with_tdd_policy()
    data["tdd_policy"]["risk_policy"] = "high"
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(data))
    report = _write_report(tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", _VALID_BUILD_REPORT)
    code = cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)])
    assert code == 2
    assert "ERROR:" in capsys.readouterr().err


def test_build_phase_tdd_policy_exception_categories_not_a_list_is_error_exit_two(
    tmp_path, capsys
):
    data = _build_contracts_data()
    data["tdd_policy"] = {
        "risk_policy": {"high": "required"},
        "exception_categories": "nope",
    }
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(data))
    report = tmp_path / "BUILD_REPORT_X.md"
    report.write_text(_VALID_BUILD_REPORT)
    assert cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)]) == 2


def test_build_phase_tdd_policy_unknown_obligation_is_error_exit_two(tmp_path, capsys):
    data = _build_contracts_data()
    data["tdd_policy"] = {
        "risk_policy": {"high": "Required"},
        "exception_categories": ["non_executable_documentation"],
    }
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(data))
    report = tmp_path / "BUILD_REPORT_X.md"
    report.write_text(_VALID_BUILD_REPORT)
    assert cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)]) == 2


# --- --phase build, task_review (BR.task_review_missing / _dirty) -----------


def _task_review_block() -> dict[str, Any]:
    """The real top-level `task_review` shape from WORKFLOW_CONTRACTS.yaml.
    The CLI only reads `verdicts`; the rest is carried along because this
    mirrors the on-disk contract, not a CLI-specific shape."""
    return {
        "verdicts": ["clean", "clean-with-minors", "dirty", "skipped-by-policy"],
        "policy_by_risk": {
            "low": "executor_checklist",
            "medium": "selective_independent",
            "high": "independent_required",
            "critical": "independent_plus_specialist",
        },
        "fix_budget_per_task": 1,
        "dependents_blocked_on": ["dirty"],
        "enforcement": {
            "high_critical_missing": "FAIL",
            "medium_missing": "WARN",
            "low_missing": "silent",
            "no_risk_row": "silent",
            "dirty_verdict": "FAIL",
        },
    }


def _build_contracts_data_with_task_review() -> dict[str, Any]:
    data = _build_contracts_data()
    data["task_review"] = _task_review_block()
    return data


# `_VALID_BUILD_REPORT`'s Task Execution table has no dedicated Task ID
# column — the parser reads cells[1] (here, the Task description) as the
# task id, so a real-looking id is substituted in directly. No `tdd_policy`
# block is added to this test's contracts data (Risk Level high + TDD Mode
# off would otherwise independently FAIL via BR.tdd_required_by_risk),
# keeping these tests focused on task_review alone.
_VALID_BUILD_REPORT_HIGH_RISK_WITH_TASK_ID = _VALID_BUILD_REPORT.replace(
    "| 1 | Implement feature | python-pro | ✅ |", "| 1 | TASK-001 | python-pro | ✅ |"
).replace(
    "| **TDD Mode** | off |\n",
    "| **TDD Mode** | off |\n| **Risk Level** | high |\n",
)


def test_build_phase_task_review_missing_high_risk_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = _build_contracts_data_with_task_review()
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(data))
    report = _write_report(
        tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", _VALID_BUILD_REPORT_HIGH_RISK_WITH_TASK_ID
    )
    code = cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)])
    assert code == 1
    out = capsys.readouterr().out
    assert "VERDICT: FAIL" in out
    assert "BR.task_review_missing" in out


def test_build_phase_task_review_key_absent_leaves_rule_off_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = _write_build_contracts(tmp_path / "contracts.yaml")  # no task_review key
    report = _write_report(
        tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", _VALID_BUILD_REPORT_HIGH_RISK_WITH_TASK_ID
    )
    code = cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)])
    assert code == 0
    out = capsys.readouterr().out
    assert "VERDICT: PASS" in out
    assert "BR.task_review_missing" not in out


def test_build_phase_task_review_verdicts_not_a_list_is_error_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = _build_contracts_data()
    data["task_review"] = {"verdicts": "clean"}
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(data))
    report = _write_report(tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", _VALID_BUILD_REPORT)
    code = cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)])
    assert code == 2
    assert "ERROR:" in capsys.readouterr().err


# --- --phase design / build, traceability (TX.* / BR.must_uncovered) -------


def _design_contracts_data_traceability_only() -> dict[str, Any]:
    """Real `traceability.verification_types` 10-type vocabulary, no
    `task_manifest` key at all — `--phase design` routing arms on
    `task_manifest` OR `traceability`, so this exercises the `traceability`
    alone leg."""
    return {
        "design": {"required_sections": _DESIGN_REQUIRED_SECTIONS},
        "traceability": {
            "verification_types": [
                "unit",
                "integration",
                "contract",
                "e2e",
                "browser_accessibility",
                "security",
                "migration_rollback",
                "data_quality",
                "observability",
                "deterministic_inspection",
            ],
        },
    }


_DESIGN_DOC_WITH_BROKEN_MATRIX_NO_MANIFEST = """\
# DESIGN: CLI_SAMPLE

## Architecture Overview

Sample architecture overview.

## Components

Sample components.

## Key Decisions

Sample key decisions.

## File Manifest

Sample file manifest.

## Traceability Matrix

| # | REQ | Priority | Tasks | Tests | Verification Type |
|---|-----|----------|-------|-------|-------------------|
| 1 | REQ-1 | MUST | - | tests | unit |

## Code Patterns

Sample code patterns.

## Testing Strategy

Sample testing strategy.
"""


def test_design_phase_traceability_only_broken_matrix_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(_design_contracts_data_traceability_only()))
    doc = _write_design_doc(
        tmp_path / "DESIGN_CLI_SAMPLE.md", _DESIGN_DOC_WITH_BROKEN_MATRIX_NO_MANIFEST
    )
    code = cli.main([str(doc), "--phase", "design", "--contracts-file", str(contracts)])
    assert code == 1
    out = capsys.readouterr().out
    assert "VERDICT: FAIL" in out
    assert "TX.must_without_task" in out


def _build_contracts_data_with_traceability() -> dict[str, Any]:
    """The top-level `traceability` block is boolean-only on the build side
    (`isinstance(data.get("traceability"), dict)` — no subkey validation),
    so any mapping arms `matrix_must_coverage=True`; the real
    `verification_types` vocabulary is carried along to mirror the on-disk
    contract shape, not because the build side reads it."""
    data = _build_contracts_data()
    data["traceability"] = {
        "verification_types": [
            "unit",
            "integration",
            "contract",
            "e2e",
            "browser_accessibility",
            "security",
            "migration_rollback",
            "data_quality",
            "observability",
            "deterministic_inspection",
        ],
    }
    return data


_BUILD_REPORT_HIGH_RISK_UNCOVERED_MUST = _VALID_BUILD_REPORT_HIGH_RISK_TDD_OFF + (
    "\n## Traceability Matrix\n\n"
    "| # | REQ | Priority | Tasks | Tests | Verification Type | Result | Review |\n"
    "|---|-----|----------|-------|-------|-------------------|--------|--------|\n"
    "| 1 | REQ-1 | MUST | TASK-A | - | unit | Pass | clean |\n"
)


def test_build_phase_traceability_matrix_uncovered_must_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(_build_contracts_data_with_traceability()))
    report = _write_report(
        tmp_path / "BUILD_REPORT_CLI_SAMPLE.md", _BUILD_REPORT_HIGH_RISK_UNCOVERED_MUST
    )
    code = cli.main([str(report), "--phase", "build", "--contracts-file", str(contracts)])
    assert code == 1
    out = capsys.readouterr().out
    assert "VERDICT: FAIL" in out
    assert "BR.must_uncovered" in out


def test_design_phase_traceability_verification_types_not_a_list_is_error_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Only the design side validates `traceability.verification_types`
    (`_design_phase_contract`); the build side treats `traceability` as a
    boolean presence flag with no subkey validation (see
    `_build_contracts_data_with_traceability`'s docstring), so this
    malformed-shape check targets `--phase design`."""
    data = _design_contracts_data_traceability_only()
    data["traceability"]["verification_types"] = "unit"
    contracts = tmp_path / "contracts.yaml"
    contracts.write_text(yaml.safe_dump(data))
    doc = _write_design_doc(tmp_path / "DESIGN_CLI_SAMPLE.md", _VALID_DESIGN_DOC)
    code = cli.main([str(doc), "--phase", "design", "--contracts-file", str(contracts)])
    assert code == 2
    assert "ERROR:" in capsys.readouterr().err
